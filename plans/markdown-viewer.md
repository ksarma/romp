# The markdown viewer: reading a note as GitHub and Obsidian show it

**Status: BUILDING. Approved by the user on 2026-09-07 with rulings on all eight decisions**, recorded
under Decisions as rulings; exact table and code mapping became Slice 8 by ruling 7. Being built by a
dedicated romp session as eight fork PRs in the order 1, 2, 3, 4, 5, 8, 6, 7, each through an
adversarial review and a full test sweep; a "The Slice N build" note under a slice records where the
code as built departs from this text and why. Six-lens audit at the fork's origin/main 1e829313
(2026-09-07), each of the 75 findings reproduced in headless Chromium; the raw findings stay outside the
repo. File and line references describe the fork at that audit commit; as with every plans/ document,
treat them as dated. Excluded as in flight at audit time: text size, fluid width and table reflow
(fork PR #348, merged) and links inside viewed files (fork PR #347, open at this commit); the slices
build on both. The upstream fold (fork PR #349), also merged after the audit, already mints
`md-`-prefixed GitHub-slug heading ids and lands in-document `#` links on their heading, so the ninth
High defect below is partly closed on main; Slice 4 keeps that prefix and builds on it.

## Summary

When built, a note in the viewer reads as on GitHub or in Obsidian: headings show structure, tables
and figures keep their shape at any width, front matter, callouts, math, footnotes and wikilinks
render as written, heading links jump, a session's edit never moves the reader, comments anchor on
any passage, and every failure says what happened.

The audit confirmed 75 defects, nine high; eight slices fix them, each useful alone and one
session-day. The user ruled on the eight decisions the audit raised; the rulings are recorded under
Decisions, and each slice names the decisions it carries: 6 in Slice 1, 3 and 4 and 5 in Slice 3,
1 and 2 and 8 in Slice 4, 7 as Slice 8.

## Why now

The rendered view uses the chat's markdown rules, tuned for short replies, and the sanitizer trusts
a note's HTML. This view is now where the user reads a session's report, comments on it and accepts
its changes; two high defects hit that loop: the Comments panel never folds (380px pane: 209px body
beside a 171px panel), and a reload after a session's write loses the reader's place.

## Defects

### High

- **Comments aside never folds** (`ui/webview/styles.css:3741`, `feed.css:1569`): `.fileview-main`
  is both container and subject; the only test (`file-comments.test.ts:854`) matches CSS text.
- **Reload after a session edit loses the place** (`file-view.ts:948`). `replaceChildren` with no
  scroll bookkeeping; 20 paragraphs inserted above moved the top passage from 25 to 5.
- **Heading scale collapses** (`styles.css:3697`). h1 16.9px, h2 14.95, h3 13.65, h4 13 (equal to
  `strong`), h5 10.79, h6 8.71; no bottom rules.
- **Table cells break mid-word** (`styles.css:3691`). `overflow-wrap: anywhere` inherits into th/td;
  at 380px cells read "C/ol/u/m/n".
- **A note's HTML restyles the page** (`file-view.ts:1688`, `render.ts:1095`). DOMPurify keeps
  `<style>`, `style` and `id`; a `<style>` block blanked the page, a fixed div covered the close
  button.
- **A form in a note navigates the pane away** (`file-view.ts:1688`). `<form action=...><button>`
  submits; the Files document leaves for the action URL.
- **Front matter renders as a rule and an h2** (`file-view.ts:1685`). Every Obsidian note opens with
  `<hr>` and its keys as a setext heading.
- **An unclosed HTML wrapper swallows later blocks for comments** (`anchor-map.ts:756`). After `<div
  align=center>` or `<details>`, later selections are refused as "an HTML block".
- **No heading ids, no outline; `#section` links open a blank tab** (`file-view.ts:1696`). 0 of 31
  headings carry an id; every `a[href]` gets `target=_blank`.

### Medium

The Rendered/Raw toggle drifts about 600px (`file-view.ts:948`); a sized `<img>` is squashed
(`styles.css:3724`); the modal title bar clips at 380px (`styles.css:3544`); the Comment float
ignores body scroll (`file-comments.ts:1598`); the note bar scrolls away with the body
(`file-view.ts:874`); task items show bullet plus checkbox (`styles.css:3698`);
light-theme notes are monospace (`styles.css:275`); math renders only in the chat page, its
viewer included, and the Files and feed panes' viewers show TeX as text (`render.ts:103`); fenced code lacks a wrap gutter and Copy, ten grammars (`file-view.ts:1699`);
table alignment is discarded (`styles.css:3722`); print gives one clipped grey page
(`files-pane.css:6`); Obsidian syntax stays literal: `[[Note]]`, `![[img]]`, `==mark==`,
`> [!note]`, `[^1]` (`file-view.ts:81`); inline math makes its paragraph uncommentable in the chat
pane (`anchor-map.ts:514`); code-line comments containing `*` or `_` never paint, and one that opens a
code line with `# ` paints from two characters in (`anchor-map.ts:1034`); table cells and code refuse
Rendered selection (`anchor-map.ts:873`); a
highlight in a closed `<details>` is unreachable (`file-comments.ts:2322`); the viewer never takes
focus (`file-view.ts:766`); scroll position is lost across file switches
(`file-view.ts:484`); a render exception dumps the source as one unannounced paragraph
(`file-view.ts:1689`); a missing figure shows a wordless broken-image glyph (`file-view.ts:1738`);
browser and host disagree on BOM offsets; Save drops the BOM (`tools/file-comments-host.mjs:724`); a
failed reload never tells the seam; the panel waits 15 s (`file-view.ts:1566`).

### Low

Pane bar 96px tall at 380px (`files-pane.css:26`); code-comment colour 2.86:1
(`styles.css:81`); th fill 1.08:1, no striping (`styles.css:3721`); 1.4em list gutter
(`styles.css:3698`); 13px type, 125-character measure, left-pinned (`styles.css:3691`); `<kbd>`
unstyled (`styles.css:160`); tab-size 8 versus Raw's 4 (`styles.css:3716`);
`video`/`audio`/`source` src not rewritten (`file-view.ts:1738`); remote images fetch on open
(`file-view.ts:1741`); `:emoji:` literal (`file-view.ts:81`); a Raw comment across two cells never
paints (`anchor-map.ts:1049`); overlapping marks nest (`anchor-map.ts:1027`); a refusal
names a later obstacle (`anchor-map.ts:871`); paintAll passes no hint (`file-comments.ts:1824`); a
keyboard selection never offers Comment (`file-view.ts:995`); no open-at-heading or offset
(`path-links.ts:123`); a Latin-1 file loses Edit silently (`file-view.ts:917`); an empty file is a
blank pane (`file-view.ts:1685`); a changed file goes unnoticed, panel closed (`file-view.ts:1506`);
a CR-only file is one Raw row (`file-view.ts:1652`).

## Proposals

CSS lands byte-equal in both sheets (the parity test); layout is asserted in headless Chromium
(browser legs), not by matching CSS text.

### Slice 1: sanitize as GitHub does

`FORBID_TAGS: style, form, button, select, textarea` and `FORBID_ATTR: id, name` (`style` per
decision 6) in both sanitizers; `contain: layout` on `.fileview-md`; a delegated `submit`
preventDefault. Acceptance: sanitized fixtures hold no `<style>`, `<form>` or `id`; over the fixed
div, `elementFromPoint` at the close button's centre returns the button; clicking the form fixture
leaves `location.href` unchanged; a task checkbox still renders. Tests: source pins; one browser leg.

**The Slice 1 build** (2026-09-07). Branch `mdviewer-s1`, stacked on this plan's branch (fork PR #369) until that
merged on 2026-09-07; fork main, which carries the plan and fork PR #347, was merged in on 2026-09-08 as
`mdviewer-s1`. Where the code as built departs from the text above, why, and which test holds each rule:

1. *One shared module.* The chat's `md()` and `userMd()` (render.ts) and the viewer's `mdBlock` (file-view.ts) spelled
   the same DOMPurify profile twice. Both now call `sanitizeMd` in `ui/webview/md-sanitize.ts`, the dashboard's only
   `DOMPurify.sanitize` call, which returns the sanitized body for each caller's own DOM post-pass (PR links in the
   chat; heading ids and link stamps in the viewer, which adopts the body's children without a re-parse). The source
   pins moved with it; `md-sanitize.test.ts` holds the one-call rule.
2. *`SANITIZE_NAMED_PROPS: true` instead of `FORBID_ATTR: id, name`.* GitHub's own rule: an author's `id` and `name`
   are kept, prefixed `user-content-`, so `<a name="install">` and `<p id="top">` remain link targets under their
   prefixed names, and clobbering and collisions with the viewer's own ids are prevented either way. The viewer's
   heading ids (`md-<slug>`) are minted after the sanitize and never gain the prefix (md-url-view.test.ts pins the
   order). Fork PR #347 (links inside viewed files) was folded on 2026-09-08: `userContentTarget` (md-sanitize.ts) is
   the one lookup for an author's target, the first element whose `id` is the prefixed spelling or the bare one, else
   the first `<a name>` with either, and `fragmentTarget` (file-view-links.ts) is that lookup plus its heading-slug
   arm, so `[go](#top)`, `[install](#install)` and a link to an author's id spelled like the viewer's own chrome
   (`#fileview-save-err`) all land on the author's element under its prefix, never on the chrome (a comparison against
   the bare spelling had left all three dead); `data-frag` and the `Go to` title keep the fragment as typed. The chat
   resolves a message's own `#` links with the same lookup (item 9). One cost, GitHub's too: an inline SVG's
   `fill="url(#g)"` no longer finds its `<linearGradient id="g">`, since the id is prefixed and the reference is not.
   file-view-links.test.ts and its browser leg hold the prefixed shapes (an author's id equal to a chrome id renders
   prefixed and is never the scroll target).
3. *A wider forbidden list.* The text names style, form, button, select, textarea. The build forbids every
   form-associated element (form, button, select, option, optgroup, textarea, fieldset, legend, label, datalist,
   output, meter, progress) and `dialog` (a `<dialog open>` paints a modal box over the note). `input` stays allowed
   for marked's task checkbox, and a post-pass in `sanitizeMd` removes every input that is not a checkbox and forces
   `disabled` on one that lacks it, so no control in a note is live. A forbidden element's text stays as prose
   (DOMPurify's KEEP_CONTENT); a `<style>` block's text goes with it (DEFAULT_FORBID_CONTENTS). For the Comments panel
   a block-level `<style>` is then an html block with no rendered node, which the anchor map (not touched by this
   slice) treats as it treats a `<script>` block or an HTML comment on main: a Rendered selection spanning the
   paragraphs around it maps, the highlight covers the visible words only, and the quote the composer shows before
   Save carries the block's source between them; main's kept `<style>` element refused such a selection (found in the
   merge review, 2026-09-08; md-sanitize-anchor-map-browser.test.ts holds the mid-line case).
   Two attributes are forbidden outright. `background`: `<td background=URL>` makes the browser fetch the URL the
   moment the note renders, with no click and no gate, and decision 8's `img[src]` gate would never see it;
   DOMPurify's html list keeps the attribute, GitHub's allowlist does not; `bgcolor` fetches nothing and stays
   (md-sanitize-background-browser.test.ts: no `background=` survives and no request leaves the host). `usemap`, with
   the `map` and `area` tags: an image map is dropped whole, as GitHub drops it. It could not work here in any case:
   the prefix rule renames `<map name="nav">` to `user-content-nav` and leaves `usemap="#nav"` as written, so no map
   an author writes binds to its picture, and a surviving `<area href>` in a file document navigated the pane, since a
   file document's links are dressed by `linkMarkdownAnchors`, a walk over `a`, which an area is not. `LINK_SEL` (item
   8) keeps naming `area[href]` as a second guard. For Slice 4's gate, not fixed here: `<svg><image href>`, `<video
   poster>`, `<img srcset>` and `<source srcset>` also fetch on open and sit outside `img[src]`.
4. *Decision 6's grammar.* An `uponSanitizeAttribute` hook, installed once behind a module guard, keeps in a `style`
   attribute only `color` and `background-color` declarations whose value is a literal colour: a bare word of letters
   (a named colour, `transparent`, `currentcolor`, or a CSS-wide keyword such as `inherit`, `unset` or `initial`,
   which the browser applies and which can only set the colour; an unknown word is a declaration the browser ignores;
   a hyphenated word such as `revert-layer` fails the pattern), `#` plus 3 to 8 hex digits, or
   rgb()/rgba()/hsl()/hsla() over 3 or 4 arguments, each a plain number or percentage with an optional angle unit
   (deg, grad, rad or turn) or `none`, separated by commas, spaces or a slash. One argument pattern serves every
   position, so an angle unit is accepted wherever it appears, though only an hsl hue can carry one; a value such as
   `rgb(1deg 2 3)` is kept in the attribute and the browser discards it. No other function and no nested parentheses
   (so no url(, var(, expression(, calc(), no `!important`, no quotes, escapes or comments. The `background` shorthand
   is not `background-color` and is dropped. The attribute is rewritten to the surviving declarations and removed when
   none survive. The hook is global to the DOMPurify instance and there is one sanitize call, so it applies on both
   pages and to inline SVG. md-sanitize.test.ts runs the grammar, the hook and the guard. Existing READMEs lose their
   positioning styles by design (`<img style="display:block;margin:0 auto">` lays out left at natural width, as on
   GitHub); Slice 2 gives figures their layout back through attributes.
5. *Containment.* `contain: layout` on `.fileview-md` in both sheets; the parity test pins `.fileview-md {`. It is the
   only rule that contains a fixed or absolutely positioned element in a note: `.fileview-main`'s `container-type:
   inline-size` (fork PR #247, the Comments panel) applies style and inline-size containment, not layout containment,
   so it forms no containing block, and on the base commit an `inset: 0` fixed box nested in a note measured the whole
   viewport, with `elementFromPoint` at the close button's centre and at the Comments aside's first button returning
   that box (headless Chromium 151, measured 2026-09-07). With the md rule the same box measures the md rect and both
   hits return the buttons. Fork PR #375 (merged 2026-09-08, folded into this branch the same day) put
   `container-type: inline-size` on `.fileview` too, for the Comments panel's fold query; it adds no containment, and
   the md rule stays. The region layer (`.fc-overlay`, absolute inside its own `position: relative` wrap), the Comment
   float (`.fc-float`, appended to `document.body`) and the `.fc-hl` highlights (inline) are unaffected: all 47
   file-comments test files pass, the regions browser leg included.
   Layout containment treats content overflowing the md box as ink overflow, but the box's height is auto, so the
   body's vertical scroll is unchanged (the browser leg scrolls a 120-paragraph note to its end) and a table or a
   `pre` keeps its own `overflow-x: auto`. A probe box in the browser leg has to be nested, not a direct child:
   `.fileview-md > :where(:not(table))` caps a direct child at the prose measure.
   Content wider than the md box is ink overflow the body cannot scroll to (on the base commit the body scrolled
   sideways to it), so the media a note draws itself is capped at the column the way `img` already was: `svg`,
   `canvas` and `video` under `.fileview-md` take `max-width: 100%`, and a PIXEL-sized one (a `width` attribute not
   ending in `%`) takes `height: auto` so it keeps its ratio as the cap shrinks it; a percentage-width element the cap
   never shrinks keeps the author's explicit height (an unconditional `height: auto` grew a full-width `<svg
   width="100%" height="30" viewBox>` to 258px and an unloaded `<video height="120">` to Chromium's default 150). A
   video's ratio is not its attributes' by construction, as an svg's and a canvas's are: the browser maps `width="640"
   height="360"` to `aspect-ratio: auto 640 / 360`, and `auto` defers to the media's natural ratio once a poster or
   the frames are there, so `height: auto` alone laid a 640 by 360 clip with a square poster out 640 by 640 in a pane
   that shrank nothing, and the box jumped to the frames' shape at play. `mdBlock` writes the attributes' ratio as a
   pixel-sized video's inline `aspect-ratio` (`keepVideoShape`, file-view.ts, module-private; a percentage in either
   attribute is left alone, as the sheet's rule leaves a percentage width), so the box is the author's shape capped or
   not, and the sheet's rule stays the one that lets it shrink. Both rules are written inside `:where()` at zero class
   specificity, so KaTeX's own `.katex svg` rule wins once math renders in a note (its stretchy glyphs carry
   `width="400em"`, pixel-like to the attribute test), and the direct-child measure rule covers them too. A no-viewBox
   svg wider than the column is cropped rather than scrolled to, the one case where the base's sideways scroll showed
   more. Byte-equal in both sheets; the parity test pins the four heads. md-sanitize-wide-media-browser.test.ts lays
   the fixtures out at 900 and 380px: the two author-sized shapes keeping their height; a square-poster clip at
   640x360, and spelled `640.5` and `640px` (spellings HTML's dimension rules and the browser's own mapping read as a
   length); the same poster on the capped 1500x40 video; a percentage-width clip that gets no ratio written; and a
   padded length and a padded percentage, which pin that the sanitizer trims every attribute value (DOMPurify, all but
   `value`), so neither the sheet's `[width$="%"]` test nor `mdBlock`'s parse ever meets whitespace.
6. *The submit backstop* is one `submit` listener calling `preventDefault` on `.fileview-body`, in `openFileView` and
   in `openUrlView`, installed once per open on the stable body before any render, so it survives every Rendered and
   Raw swap. In `openFileView` it sits with the body's one plain click listener (the #347 fold replaced that open's
   `fv-open` delegate with the listener that reads a file document's links); in `openUrlView` it sits beside the
   `fv-anchor` delegate, which that viewer keeps. The sanitizer never lets a form through, so the browser leg
   exercises the listener by inserting a real form after render.
7. *KaTeX renders after the sanitizer.* The chat's math extensions (math.ts) emitted KaTeX's markup into marked's
   output, and KaTeX carries every piece of vertical layout in inline `style` (a strut's height, a vlist row's top, a
   radical's padding), so through the colour-only rule a fraction came back on one line, a superscript at the baseline
   and a radical a hairline, while the source pin that stood for "the profile passes KaTeX" stayed green. The
   extensions now emit an inert placeholder (a span under `md-math-inline`; a span, or a div for a display paragraph
   of its own, under `md-math-display`; the TeX as escaped text), `sanitizeMd` runs, and `renderMathPlaceholders`
   (math.ts, a plain exported function) renders KaTeX into each placeholder on the sanitized DOM with
   `katex.render(tex, el, { output: "html", trust: false, maxSize: MATH_MAX_SIZE_EM, displayMode, throwOnError: true,
   maxExpand })` and unwraps it, so the `.katex` root stands where marked's output used to stand and KaTeX's styles
   never meet DOMPurify (md-sanitize-postpass-browser.test.ts measures a fraction, a superscript, a radical and a
   display sum after the pass; md-sanitize-katex-browser.test.ts holds the rendered root byte-identical to
   katex.render's own output). The fill is a post-pass `sanitizeMd` itself runs: md-sanitize.ts keeps a small registry
   (`registerMdPostPass`, idempotent per function), and chat-md.ts, the module that defines the math grammar,
   registers `renderMathPlaceholders` at load, so every `sanitizeMd` call in a bundle that carries the grammar renders
   math, the viewer's `mdBlock` in the chat page included, and a bundle without it (files.js, feed.js) has neither the
   grammar nor the fill nor KaTeX; a fill called by hand from `md()` and `userMd()` left that viewer's formulas as
   bare TeX (md-sanitize-viewer-math-browser.test.ts opens such a note in both bundles). The registry's loop has no
   per-pass try/catch: an isolated pass fails open (a gate that rewrites off-host figure sources and throws midway
   would hand back a half-rewritten body that looks fine while the rest fetches), where a throw that falls to the
   whole-message source view is visible and closed; per-element resilience is each pass's own contract, as the fill's
   per-formula belt is. Slice 4 imports the grammar module into the files and feed bundles (decision 1) and the fill
   comes with it; `mdBlock` calls nothing.
   Four bounds stand ahead of the call and a fifth inside it, each showing the formula as its source with a `title`
   saying why (a code block for a display paragraph of its own, a code span in a paragraph); the belt a residual KaTeX
   throw takes has the same shape and says so on the console once per call. Each constant is recorded with the
   measurement behind it; change one with new numbers.
   `MATH_TEX_MAX_CHARS`, 20,000 characters of TeX per formula. `katex.render` is synchronous on the main thread and
   took 0.23 s at 20,000 characters, 0.8 s at 24,000, 6 to 17 s at 100,000, and had not finished 1,000,000 after 270
   s, while KaTeX has no option that bounds its input and no tokenizer bounds a formula, so one enormous formula in a
   reply or a note froze the chat page and every session tab in it. The postpass leg runs the cap for real: at the cap
   KaTeX renders, one over shows the source, 200,000 characters in milliseconds.
   `MATH_TEX_BUDGET_CHARS`, 100,000 characters per `renderMathPlaceholders` call, one message or one note. Twenty
   formulas just under the cap handed KaTeX 400,000 characters and blocked the page for 8 to 15 s (the render, then
   the layout of 1,200,000 elements); past the running total a formula is shown as source with the total in its title,
   and a shorter one that still fits renders. Five caps is several hundred ordinary display equations, more than a
   long paper's mathematics (the postpass leg: twenty near-cap formulas render five and show fifteen, a short one
   after them still renders; its time bound is a ceiling, and the counts are the check). The cost per character
   depends on the shape as well as the volume (measured 2026-09-08): a one-row matrix of one-character cells lays out
   about seven elements per character where a flat sum lays out three, and five of them at the cap took 4.7 to 5.5 s
   of render and layout where five flat sums of the same volume took 1.8 to 1.9 s, the densest shape found, so that
   is the budget's worst case, while 673 ordinary display equations totalling 99,000 characters took 1.2 s. The
   budget bounds volume, not time; the worker with a time budget in the Slice 4 design note is what bounds the time
   whatever the shape.
   `maxExpand`, computed per formula by `maxExpandFor`. KaTeX expands `\def` and `\newcommand` bodies before layout
   and its count is of expansions, not their size, so `\def\a{<1,000 characters>}` and 200 uses of `\a`, 1,409
   characters as written, was 200,000 of formula and 20 s of freeze (a nested chain of 1,077 characters 22 s), and no
   fixed value closes it: the default 1,000 allows 1,000 uses of a body under the cap, and a value low enough to
   matter breaks ordinary formulas, whose `\,`, `\dots` and `\boxed` are macros that count (100 `\boxed` fail at 50).
   The count is `MATH_EXPANSION_BUDGET_CHARS` (the cap's 20,000) divided by the longest macro body the formula
   defines, never above KaTeX's default of 1,000 (a body of 20 characters or fewer leaves it in place, and a formula
   that defines no macro keeps it), since each expansion pushes at most that body, so the expanded formula is at most
   two caps' worth (0.9 s for 40,000 flat characters in node). `macroBounds` reads the bodies from the TeX as text and
   recognises a definer (`\def`, `\gdef`, `\edef`, `\xdef`, `\newcommand`, `\renewcommand`, `\providecommand`, `\let`,
   `\futurelet`, with `\global` or `\long` in front) by its token alone, whatever names the macro: KaTeX takes any
   next token but `\ { } $ & # ^ _` as the name, so `\def1{...}` and `\def\!{...}` define macros, and a scan that
   looked for a control-word name after the definer let the bombs back in under a digit. The body is the brace group
   after the definer wherever it starts (a name, parameters or a delimiter between them changes nothing), and a body
   the scan cannot place takes the strict bound, every expansion priced at the formula's own length: a definer with no
   brace group after it, a `\let` or `\futurelet` that aliases a definer (`\let\d\def \frac{a}{b} \d\b{<1,000>}` read
   `{a}` as the body), and a definer inside a brace group, stored in a macro body and run at each use, where a body
   assembled from the arguments is up to nine groups long (18,154 characters of TeX under every other bound had not
   finished after two minutes). Two shapes no count bounds are shown as source before KaTeX sees them: a body that
   uses one of its parameters more than once in any brace group (`\def\a#1{#1#1}`, 512 copies of the argument nine
   levels deep), and a body defined with `\edef` or `\xdef`, which KaTeX stores EXPANDED, charging the stored body's
   length once at the definition and one expansion per later use whatever that length (`\def\a{<20
   characters>}\edef\b{<10 uses of \a>}` and 788 uses of `\b`, 1,635 characters of TeX, was 998 expansions, 157,600
   characters of formula and 31 s of freeze); no ordinary notation needs either. The count over-approximates in one
   direction, recorded and left as is: once a formula defines a body longer than 20 characters every expansion is
   priced at that body, the built-in macros' included (`\,` costs 3, `\dots` 2, `\boxed` 1), so a 200-character body
   used once beside 34 `\,` is refused where plain KaTeX renders it; no exact price exists, since KaTeX counts
   built-ins and defined macros alike. The call therefore runs with `throwOnError: true`, and KaTeX's expansion stop
   ("Too many expansions") is shown as source with the reason and the count in its title, as the other bounds are,
   while any other syntax error is rendered again with `throwOnError: false`, KaTeX's own red text as on main.
   render-math.test.ts executes `macroBounds` and `maxExpandFor` over every definer form, the digit and control-symbol
   names, the alias and the nested definer, and pins the order of the bounds and the two calls; the postpass leg runs
   the bombs under every name, the decoys, a 200-character body used 150 times shown as source, ordinary macro use
   rendering and a syntax error in red, each in milliseconds.
   `maxSize` (`MATH_MAX_SIZE_EM`, 50, about the chat column) caps the sizes a formula asks for. KaTeX's default is
   Infinity, and `\rule{5000em}{5000em}` laid a 78,650 px square in the transcript, `a\kern{50000em}b` a line 786,520
   px wide beyond the page's `overflow-x: hidden`; ordinary layout never nears it and renders byte for byte as it does
   without the option (md-sanitize-katex-browser.test.ts holds the identity against katex.render's own output: the
   fill's markup is the DOM path's, which sets `class=""` on a classless span and serializes styles with a space after
   each colon, so it differs from main's string-renderer markup in those bytes alone, with every rect and every text
   the same, and nothing reads the bytes; found in the merge review, 2026-09-08). The cap is on each size a formula
   asks for, not on their sum: a row of a thousand capped rules is clipped by the column as any long inline formula is
   and the transcript keeps its shape, while a column of a thousand `\rule{1px}{49em}` rows in a display array (18,051
   characters, under the length cap) is some 776,000 px tall where a thousand plain rows are 19,000 px, identical on
   main; the two length caps bound it, and a bound on the rendered box's height would be a new mechanism, not built
   here.
   The source fallback was indistinguishable from a code span the author wrote (every computed property equal; the
   title is the one marker, and a phone has no hover): its code element wears `md-math-src` (`MATH_SOURCE_CLASS`) and
   one rule, byte-equal in styles.css and feed.css and pinned by fileview-parity.test.ts, dresses it in the dim tier
   with a dotted underline, tokens only; render.ts's highlighter leaves the element alone (auto-detection over 20,000
   characters of TeX cost 250 ms and coloured it as a guessed grammar). In the user's own bubble that rule lost to the
   bubble's code rule (`.user-bubble :not(pre) > code`, which outranks it), so a formula the user typed came back
   white, as a code span they wrote, under a `var(--dim)` underline near 1.7:1 on the fill; a second rule in
   styles.css alone (the bubble's rules live in no other sheet) gives the code SPAN the bubble's dim tier, the
   blockquote's white tint, for its text and its underline, and leaves the block shape to the page-coloured well,
   where `var(--dim)` reads as it does in `.md` (md-sanitize-katex-browser.test.ts lays both shapes out under the
   whole sheet in both themes).
   An author who hand-writes the placeholder gets only what KaTeX renders from TeX under `trust: false` (no \href,
   \htmlStyle, \includegraphics, \htmlClass); no class name is special-cased, and the colour-only rule is unchanged.
   In a bundle that carries the grammar (the chat page's viewer, today) that paragraph's rendered text then differs
   from its source, so the anchor map refuses it with the Raw view offered, never mis-anchored, as it refuses a
   paragraph carrying `$x^2$` there already (the Medium defect Slice 5's math holes take up); the Files page, with no
   grammar, maps it as main did (found in the merge review, 2026-09-08). The svg profile now serves a note's own
   inline SVG, not KaTeX. SECURITY.md's output-sanitization bullet records the boundary: KaTeX is the one renderer
   that writes into the sanitized DOM after DOMPurify has run, under `trust: false` and these bounds;
   md-sanitize.test.ts holds the bullet to this section and to the code.
8. *Every link element.* DOMPurify's html profile kept `<map>` and `<area>`, and its svg profile keeps an SVG `<a>`
   with `href` or SVG 1.1's `xlink:href`; `mdBlock`'s two link passes and the chat's click delegate ran over
   `a[href]`, which reaches only an HTML anchor (an area is not an anchor, and `[href]` matches the null-namespace
   attribute alone), so an `<area href>` or an SVG `<a xlink:href>` in a note or a chat message navigated the pane's
   document to its URL in the same frame. md-links.ts exports `LINK_SEL` (`a[*|href], area[href]`) and `linkHref`
   (`href`, else `xlink:href`); `mdBlock` copies an xlink-only href to a plain `href` first, and writes `target` and
   `rel` with `setAttribute` (an SVGAElement's `target` property is a read-only SVGAnimatedString, so the property
   write was dropped without a word); the chat's delegate keys on the same selector and reads the same function. After
   the #347 fold, `mdBlock`'s two `LINK_SEL` passes serve a URL document (resolution against the URL; the fv-anchor
   stamp and the new-tab stamps), and a file document's links are dressed by `linkMarkdownAnchors`
   (file-view-links.ts), whose walk over `a` reaches the SVG anchor too because its `xlink:href` was copied to `href`
   first: an SVG `<a href="sibling.md">` becomes the same path link a relative `<a>` becomes and opens the sibling in
   the viewer. The XLink attribute is REMOVED after the copy: `linkMarkdownAnchors` takes `href` off a path link and a
   dead link, and the browser follows `xlink:href` when `href` is absent, so a copy that left it in place navigated
   the Files document in the same frame from a dead SVG link (`<a xlink:href="127.0.0.1:3000">`) and let the chat's
   delegate, which matches `a[*|href]`, open a path link's `sibling.md` as a URL document resolved against the chat
   page instead of the sibling file. An `href` the author wrote beside the xlink wins, as in the browser. Image maps
   are dropped (item 3); `area[href]` stays in `LINK_SEL` as a second guard. md-sanitize-viewer-links.test.ts, its
   browser leg and md-sanitize-chat-links-browser.test.ts click every shape (item 10).
9. *In-page anchors in a chat reply.* A reply's own `<sup id="fn1">` and `<a href="#fn1">`, or `[install](#install)`
   over its `<a name="install">`, scrolled the transcript on main through the browser's default fragment lookup; with
   the id and name prefixed and the href left as written, that lookup found nothing and the click died. render.ts's
   capture-phase link delegate now resolves a `#` href inside a message body the way GitHub's page script does:
   `userContentTarget` over the message's own body first (its footnote before a same-named element in an older
   message), then over the document; found, the target is scrolled into view (`block: "start"`) and the default
   cancelled, so the hash stays as it was; not found, the click is left to the browser as before. A click the browser
   answers with a tab or window of its own (Shift; Cmd on macOS, Ctrl elsewhere: `browserTabClick`, md-links.ts) keeps
   the browser's, read by the platform's key, because Super-click on Linux and Windows is a plain click to the
   browser, and standing aside for Meta there left the default lookup to find nothing; it is resolved like a plain
   click now, and render.ts's nav-chord handler reads the same `IS_MAC`. A link outside a message body (the viewer's
   own section links, which the viewer lands itself) is not this branch's. Before the scroll the target is revealed as
   the browser's fragment navigation reveals it (the HTML spec's ancestor revealing steps): every closed `<details>`
   whose content holds it is opened, and a `hidden="until-found"` on it or an ancestor is removed, since
   `scrollIntoView` does neither, and a reply's link over a note folded into a `<details>`, which the default action
   opened on main, left the fold closed with the click already cancelled (found 2026-09-08). A target in a details'
   own `<summary>` is in view already and opens nothing, as in the browser. md-sanitize-chat-links-browser.test.ts
   clicks both shapes, a nested fold included.
   The scheme test that follows no longer hands a scheme-less href to the browser's default action (pre-existing on
   main). DOMPurify keeps several hrefs that fail that test and still resolve to another origin: protocol-relative
   `//host` and `/\host`, an `https:` behind a C0 control character (its trim removes JavaScript whitespace only, and
   its URI check strips controls for the test and writes the value back as written) and a tab or newline inside the
   scheme (`ht&#10;tps:`); a click on any of them navigated the chat document itself, in the same frame, to that
   origin, and a plain relative link did the same to a same-origin page. The delegate now resolves such an href the
   way the default action would, `new URL(href, document.baseURI)` (the browser's own parser drops the control and the
   whitespace and gives `//host` the page's scheme), and opens the RESOLVED address as it opens an absolute one: a
   tab, or the viewer for a same-origin `.md`; an empty href (`[x]()`, which the default action would reload the page
   for) is inert on any click, a Ctrl- or Shift-click included, since the arm owns the click whatever the modifier and
   the base's tab was a second copy of the dashboard, not a destination the author named; a non-web result (VS Code's
   webview scheme, where every relative href resolves) or a parse failure stays the browser's, as before.
   md-sanitize-chat-schemeless-browser.test.ts clicks each shape over the real bundle.
   Both branches read a MESSAGE's link only: the body scope is read once ahead of them (`.md`, or null for an anchor
   carrying the page's `data-act`, the body delegate's), and an anchor outside a message body is the browser's. The
   scope names one body more than `.md`: a comment thread's agent reply in the popover's msgs projection
   (`div.cmt-msg.agent`, `commentMsgEl`), the one body `md()` fills that wears no `.md` and stands on `document.body`
   with none above it, where a reply's own `#` link did nothing and a scheme-less link navigated the chat document in
   the same frame; the class is read there rather than `.md` added to the reply, since `.md` is also the chat's
   typography and the comment highlight's host rule (md-sanitize-chat-links-browser.test.ts clicks both links in a
   mounted popover). The delegate is document-wide, and the page itself builds scheme-less anchors, `<a
   href="/file?..." download>`, for its three download controls (the lightbox's control, preview.ts; the viewer's
   Download button and the file browser's download row, a transient anchor each button clicks): an arm that resolved
   those too handed them to `window.open`, a popup where the download was, nothing at all under a popup blocker, and
   the lightbox's picture opened in a tab and was never saved, where main let the browser's anchor download run. A
   message's own same-origin download link (DOMPurify keeps `download`) is the browser's too, since the browser
   honours a same-origin download attribute whatever the response says and never moves the frame for it; a download
   link to another origin, whose attribute the browser ignores and would navigate for, opens as any other link. The
   schemeless leg presses each real control in the render bundle (the download awaited as the page's own event) and
   clicks both message shapes; chat-link-open.test.ts and md-url-view.test.ts pin the scope.
10. *Tests*, by file. Every browser leg runs in headless Chromium over the real bundles, resolves playwright and
   esbuild through the extension's package.json (a bundle written outside vscode-extension used to skip with a false
   diagnosis; md-sanitize-browser.test.ts pins the idiom for the family), and skips loudly without a browser. What a
   click did is read from the browser's own events, not from a timer, with two timed waits left standing:
   md-sanitize-browser.test.ts waits 150 ms after the click on the form's text before reading `location.href` (the
   acceptance item above; its step 6 reads the same over the whole leg from the main frame's navigations and the
   off-host requests the page reports) and 100 ms after a real form's submit before reading the result, and
   file-view-links-browser.test.ts's `settle` (a frame and 80 ms), inherited from main, follows the section link this
   slice clicks, plain and with Ctrl, and the scroll back between the two clicks, as it follows the rest of that leg.
   `md-sanitize.test.ts` (node): the colour grammar, the hook, the module guard, the profile, the one-call and CSS
   pins, the registry and its loop, the guide's paragraph, and SECURITY.md's output-sanitization bullet, held to this
   section's bounds and to the code (KaTeX renders after DOMPurify under `trust: false`). `md-sanitize-guide.test.ts`:
   the guide's `<style>` clause (its text goes with it; a form's and a `<dialog>`'s stays), its link clause (the
   target decides, not the element) and its colour clause (the forms the grammar keeps are named; no promise that
   every coloured span keeps its colour).
   `md-sanitize-browser.test.ts`: the fixture over the real files bundle, an author's `data-*` fixture, a whole-leg
   log of main-frame navigations and off-host requests. On the base commit it times out waiting for `.fileview-md`:
   the fixture's `<style>` block hides the viewer, the audit's defect reproduced.
   `render-math.test.ts` (node): the placeholder contract; the katex.render options and the two calls; the render.ts
   wiring; the order of the fill's bounds (the macro bounds read once, for the two refusals and the count); the
   constants, the class, the sheets' rule and the highlighter's exemption.
   It executes `macroBounds` and `maxExpandFor` over the definer forms (`\def`, `\gdef`, `\edef`, `\xdef`,
   `\newcommand` braced and unbraced, `\renewcommand`, `\providecommand`, `\DeclareMathOperator`, `\global` and
   `\long` in front, a digit and a control symbol as the name, `\let` and `\futurelet` aliasing a definer, a definer
   inside a body, no brace group after a definer, escaped braces, an unclosed body, `\deficit` and `\def@` as other
   words), the bomb and the decoys stopping under the computed count, ordinary macro use under the default, the
   `\rule` cap, and the `\edef` cost model (fifty uses of an `\edef` body render 10,000 characters of formula under a
   count the same shape spelled with `\def` stops at). `md-sanitize-math.test.ts`, a near-copy, was folded into it.
   `md-sanitize-postpass-browser.test.ts`: a fraction, a superscript, a radical and a display sum measured after the
   post-pass; an author's style beside them keeps only colour; hand-written placeholders under trust: false; the
   forced-disabled checkbox clicked; the formula cap (at the cap KaTeX renders; one over, the source as a code block
   or a code span with its title; 200,000 characters in milliseconds); every macro bound over the pipeline (the bomb,
   the chain, the argument repeat and the `\edef` bomb, each also under a digit name, `\global` in front, a
   control-symbol name, the alias decoy, and a 200-character body used 150 times: the source with the reason, in
   milliseconds where they froze 20 to 31 s; ordinary macro use renders; a syntax error is KaTeX's red span);
   `\rule{5000em}{5000em}` and `a\kern{50000em}b` measured under the cap; twenty near-cap formulas rendering five and
   showing fifteen as source, a short formula after them still rendering; the fallback's computed dress beside an
   author's code span in both shapes.
   `md-sanitize-katex-browser.test.ts`: the rendered `.katex` is byte-identical to katex.render's own output, a capped
   `\rule` included, and differs from the uncapped call; the userMd path; the registry's idempotence; the source
   fallback laid out under the whole of styles.css in the user's bubble and the assistant's `.md`, both shapes, both
   themes. `md-sanitize-viewer-math-browser.test.ts`: a note with a fraction, a radical and a display sum opened from
   a chat message renders KaTeX in the chat page's viewer, with its layout styles and the numerator above the
   denominator; the same note through the files bundle keeps its TeX as literal text, and files.js carries neither the
   grammar nor KaTeX.
   `md-sanitize-viewer-links.test.ts` and its browser leg: LINK_SEL in mdBlock; an SVG anchor's absolute, fragment and
   relative hrefs clicked in a file document (stamps linkMarkdownAnchors') and in a URL document opened with no
   delegate in front (mdBlock's own setAttribute stamps decide between a new tab and a same-frame navigation); the SVG
   anchors whose stamps take the href off, spelled `xlink:href` (a relative `sibling.md`, a host with a port), clicked
   in the Files page and over the real chat bundle with the file document opened through `openFileView`, no
   `xlink:href` left on any anchor; a dropped image map's inert picture; the node leg runs the pass's own source over
   stand-in anchors (xlink only, both, href only). What a click did is read from the Navigation API's `navigate`
   record and CDP's `Target.targetCreated`.
   `md-sanitize-chat-links-browser.test.ts`: the same shapes clicked in the chat; a footnote's back link, a link over
   the reply's own `<a name>`, a same-named target in an older message and a fragment with no target, each read from
   the click's own `defaultPrevented` flag; a comment popover's agent reply mounted, its `#` link (the list scrolls,
   the hash stays) and its root-relative link (opened, the document kept) clicked; a target inside two nested closed
   `<details>` and one under `hidden="until-found"`, each revealed and scrolled to the transcript's top, the hash
   kept.
   `md-sanitize-chat-schemeless-browser.test.ts`: each scheme-less shape clicked over the real chat bundle, the
   resolved address opened and the document kept; the page's three download controls pressed (the real lightbox,
   viewer and file browser openers in the render bundle; the browser's download event awaited, no `window.open`, the
   anchor's click uncancelled), and a message's same-origin and cross-origin download links clicked.
   `md-sanitize-chat-modified-click-browser.test.ts`: Shift and the platform's tab key are left to the browser and
   Super off macOS scrolls, read from each click's own record (`defaultPrevented` at the end of dispatch, the keys it
   carried, the target) plus the scroll offset, the hash and the window.open log, never from the tab Chromium opens,
   which came late or never under load.
   `md-sanitize-background-browser.test.ts`: no `background=` survives and no request leaves the host.
   `md-sanitize-wide-media-browser.test.ts`: the media caps at 900 and 380 px, the author-sized shapes keeping their
   height, the poster clip in every spelling of a length, the sanitizer's trim.
   `md-sanitize-anchor-map-browser.test.ts`: the real sanitizer and the real anchor map, adopted as `mdBlock` adopts:
   a mid-line `<style>` or `<script>` loses its text and the Rendered mapping refuses the paragraph as a rendered-text
   mismatch with the Raw view and the exact range offered, never mis-anchored; a mid-line `<textarea>` keeps its text
   and maps, as does a plain paragraph; a node subtest pins that the difference is DOMPurify's FORBID_CONTENTS, not
   the profile.
   Pins moved to the shared module or the fold: `chat-link-open.test.ts` (`userContentTarget` executed; the arm's
   message-only scope, `commentMsgEl` included; the download rule), `md-url-view.test.ts` (the heading-id order; the
   scope; the download rule), `file-view.test.ts` (the new-tab pin scoped to `mdBlock` and `linkMarkdownAnchors`,
   since a whole-file match stayed green with the stamps deleted), `file-view-links.test.ts` and its browser leg (the
   prefixed shapes; a chat-host prelude that defines `browserTabClick` and `IS_MAC`, lifted from render.ts, with a
   guard that reads every import form and every top-level declaration of render.ts and lists any name the lifted
   opener uses that the prelude lacks; a section link clicked plain and Ctrl-clicked, and a query-only link),
   `md-links.test.ts` (`browserTabClick`), `fileview-parity.test.ts` (`.fileview-md {`, the four media heads and the
   fallback rule byte-equal in both sheets), `anchor-map.test.ts` (its header names the one text the sanitizer drops),
   the regions legs' docstrings (their styled figures pin the layer's contract, not what a note renders as under
   decision 6), and chat-md, pr-links, render-sanitize, file-view-seam and file-view-text-size.

### Slice 2: layout follows the pane, reader keeps their place

`container-type: inline-size` moves to `.fileview`; `overflow-anchor: none` on the body; renderBody
restores the top-visible block's source offset across a swap; `height: auto` on figures; the Comment
float hides on body scroll. Acceptance: at 380 and 640 `.fileview-main` computes `flex-direction:
column` with a pane-wide body; a reload inserting 20 paragraphs above keeps the top block; the
Rendered/Raw round trip returns to the same scrollTop; a 3:1 picture with sized attributes renders
3:1; every bar button sits inside the card at 380px; the note bar, mounted above the main row,
survives body scroll. Tests: browser legs replacing the text assertion at
`file-comments.test.ts:854`.

**The Slice 2 build** (2026-09-08). Branch `mdviewer-s2`, stacked on `mdviewer-s1` (fork PR #390). The gap analysis
behind it ran every criterion above in headless Chromium over the real viewer at the Slice 1 tip (81cf9a92); the
numbers below are its and the build's. What earlier changes had already done, where the code as built departs from the
text, and which test holds each rule:

1. *Already done.* The fold held before this build: fork PR #375 put `container-type: inline-size` on `.fileview`, the
   viewer's card, and at 380 and 640px `.fileview-main` computed `flex-direction: column` with the body the row's
   whole width in the Files pane, the chat modal and the feed modal (pane 380: main, body and aside all 380; chat 380:
   card 361, body 359). The bar's controls sat inside the card at 380px (and 320px) since fork PR #348 made the bar
   wrap; file-view-text-size.test.ts asserts it at 380, 420, 480 and 600px in both modals. Neither needed code here.
2. *The reader's place, kept in the file's own terms* (`ui/webview/reader-place.ts`; the text says "the top-visible
   block's source offset", and that is what it is). Before every paint of a text view readPlace records the
   top-visible BLOCK, one of the top-level blocks the lexer finds in the file (anchor-map.ts sourceBlockSpans, the
   same placement the rendered index pairs elements by, so both views name the same blocks; renderedBlockIndex and
   renderedBlockElements read the Rendered side), and after the paint seatPlace finds the block in the new view and
   scrolls the body so it sits where the block sat. The place is the block's source span, how far its top edge sits
   from the body's top, its box's height, whether the body stood at its very top, the spans of the blocks on either
   side and, when the reader is partway into a block that shows lines, the line at the edge. The rules, each with
   the test that holds it:
   - *Reading the top block.* In Rendered the first top-level element whose box ends below the body's top edge,
     read to its block (an html block of sibling tags is one block, its boxes together); in Raw the block holding
     the first row that does, or the block after a blank row between two blocks (a blank row inside a fenced code
     block is the code block's). A binary search over the boxes' bottoms finds it, so a long document costs a
     handful of box reads per scroll frame; a box with no layout (a `<div hidden>` the sanitizer keeps) is read
     around rather than taken for one above the edge, and a floated figure that reaches below the paragraphs beside
     it is passed over for the first of those paragraphs ending below the edge, the one the reader is reading (kept
     instead, the figure is one row in Raw and moves as the paragraphs beside it grow). An html block of comments
     alone renders no element and is read past, its comments found by a left-to-right scan: an anchored regex there
     doubled its time per comment (144 s at thirty, on every Rendered paint) and read a line with a comment at each
     end as blank though the words between them render, so every block after it paired one element early
     (file-view-place-comment-blocks.test.ts). The anchor map's cache checks every child of the root by identity,
     since the Comments panel's regions layer wraps a top-level picture in a span while the panel is open.
     file-view-place-blocks-browser.test.ts and file-view-place-blocks.test.ts hold the rest; the float rule over the
     real viewer, file-view-place-float-browser.test.ts (the paragraph beside a floated figure kept across the
     switch).
   - *Seating the block.* A block that started below the edge keeps its distance. One the reader was partway into
     keeps the depth as a fraction of the block's height when the block's text is unchanged or the view changed
     (line 50 of a 120-line code block stays at the edge across the switch; 400px into a 600px figure, one row in
     Raw, comes back 400px into it), and in pixels when the write changed the block's text (30px into a paragraph
     the session appended a sentence to stays 30px in; a block now shorter by any amount moves down by the loss, to
     the edge at most, so as much of it shows below the edge as showed before). A body at its very top stays at its
     very top: the views pad 14 and 10px, and the round trip drifted from scrollTop 0 to 4.
     file-view-place-blocks-browser.test.ts; the pure part, seatedTop, in file-view-place-blocks.test.ts.
   - *The line at the edge.* When the reader is partway into a block that shows lines (any block in Raw; in Rendered a
     markdown code block, fenced or indented, whose code element shows the block's lines one for one) the line at the
     edge is kept as well, as its own source span (the Raw row's, or the code line at the edge in Rendered: the
     fence's own row since Slice 3 wrapped every fence in rows, read as a Raw row is and seated at the row's top, the
     Slice 3 build note's item 9; a code element with no rows keeps the depth rule: the viewer builds none, every
     fence having rows since Slice 3 and the math fill's source block being no code block to codeOf, so the Slice 3
     review's round 3 retired the hit test Slice 2 read such a line with) and its top (the row's), and followed
     through the edit when it stands, so line 50 stays line 50 across the switch and after lines inserted above it
     inside the block or deleted below it. A line the write rewrote, or one whose text recurs so that no copy is its
     own, is no line to follow, and the block's depth rule applies: lines 48 to 52 rewritten as two put line 47 at the
     edge, the block moved down by the three rows it lost (the Slice 2 review, over 5c0c737c, whose rule walked to the
     line after the nearest standing predecessor and seated the replacement's first line: it seated the edit's first
     line 44 rows up when every line between was a copy, since a rewritten line's neighbours inside the edit cannot
     place it exactly). An html block's `<pre>` is not a code block here: its lines and the block's are one off (the
     block's first line is the tag), and it keeps the depth rule, within a line (5c0c737c seated line 11 for line 10).
     Without the rule the block's top edge held and line 45 stood at the edge after five lines inserted above line 50,
     and the Rendered, Raw, Rendered round trip on line 50 came back within three lines; it is exact now.
     file-view-place-edits-browser.test.ts; file-view-place-html-browser.test.ts (the `<pre>`, the wrapped line); the
     pure part in file-view-place-blocks.test.ts (a rewritten row, a block whose lines recur).
   - *Following the block through a reload.* The span is followed through the edit first (followPassage, the
     composer's own follow): a block after the inserted text shifts by its length, one before it keeps its offset,
     and one found whole elsewhere is followed there. A block the write rewrote is placed by the block before it,
     followed the same way, and the block after that is seated, so a write that inserted twenty paragraphs above
     and rewrote the paragraph under the reader's eye still lands on what replaced it (the leg's fourth scene; the
     edit's own start, where a first cut landed, is the first inserted paragraph there); with that block rewritten
     too, the block after it places the kept block (a session rewriting two paragraphs and adding a preamble); with
     both neighbours gone as well, the nearest block before it that stands (the old block table walked outward,
     eight anchor searches per side inside the edit, blocks outside it free), else the nearest after (without the
     walk, paragraphs 39 to 41 deleted with twenty inserted above fell to the top of the document); only with no
     block standing on either side is the place where the edit begins. file-view-place.test.ts and
     file-view-place-blocks.test.ts (followPlace), file-view-place-browser.test.ts and
     file-view-place-edits-browser.test.ts (the scenes).
   - *A block deleted under the eye* (nothing but whitespace left between the standing neighbours) seats the block
     after it as a replacement of no height: at the edge when the deleted block reached below it, at its old
     distance otherwise. Without the rule the successor sat 30px above the edge, the reader's depth into a block
     that was gone. file-view-place-blocks.test.ts and file-view-place-edits-browser.test.ts.
   - *What the place refuses.* Where the reading is unreliable readPlace answers null and seatPlace seats nothing, so
     the viewer leaves the body's scrollTop alone, as it did before the slice, rather than seating a guess; where the
     body then lands is the browser's own (its scroll anchoring re-finds an anchor in the new content when it can:
     pane 900, a swap with the reader at 1969 landed at 2617 with no write of the viewer's; under `overflow-anchor:
     none` the number stands). One cause, in reading the Rendered view (the Raw rows pair with nothing and are read as
     they stand): every block but an html block renders as one element, an html block of sibling tags as several, and
     the anchor map's pairing across one is a resync on the blocks after it, which the map as it stands gets wrong two
     ways, both Slice 5's flattened walk to take up (the plan's High defect, an unclosed HTML wrapper swallowing later
     blocks). A block paired to several elements, and an html block paired to one, is trusted only when its own
     source, parsed by the browser's HTML parser (DOMParser), yields as many elements with the same text, whitespace
     apart: the parser the sanitizer read the block with, so entities, inline tags and line breaks decode alike on
     both sides (one form excepted, refusal (4) below) and nothing is decoded by hand; any other block's one element
     is trusted without a parse, and an html block is told from the rest by marked's lexer over its own text, the
     lexer the block table comes from, asked only for a block that opens with `<`, so a paragraph pays no lex and one
     opening with an inline tag or an autolink is trusted as its own element. (5c0c737c decoded the source itself and
     looked for the element's text in it: the decoder threw a RangeError on an entity past U+10FFFF, inside the Raw
     click and the text-size step, so the view stayed and the size was stored unpainted, and it knew six entity names,
     so a caption hanging on `&mdash;`, a badge over a tagline or a tag holding `<b>` read as swallowed and the switch
     left the numeric scrollTop, paragraph 28 on top both ways.) Refused, from whichever element is at the edge: (1) a
     wrapper the browser nests the following markdown into (`<details>` with a blank line after its summary, a centred
     `<div>`), paired to every element after it, from a swallowed paragraph, the wrapper itself, a picture or a rule
     in the run (read as the wrapper's block, a Raw switch from paragraph 80 landed on `<summary>`, 3500px up, and
     from a picture 100px in, 1750px up), and a wrapper whose closing tag is the document's last block, or is missing,
     paired to its one element, itself, holding every paragraph after it (the Slice 2 review over 66368710, which
     trusted any one element: a Raw switch from a nested paragraph 60 landed on the `<div align="center">` row with
     the passage 1395px below the viewport and came back 42px off, and paragraph 60's Raw row switched to Rendered
     borrowed the wrapper's box and landed on paragraph 43), refused from the wrapper and from a nested paragraph, in
     both directions; and a Raw row of the wrapper's own switched to Rendered seats nothing (5c0c737c seated the whole
     run, paragraph 74 at scrollTop 3585 for 360); (2) two html blocks a blank line apart (`<p>Alpha</p>` over
     `<p>Beta</p>`, a README's centred heading over its tagline), which the map pairs as nothing and both, from either
     element (5c0c737c read the second as its block and put the Raw view one row off); (3) an html block, one tag or
     several, holding a tag the sanitizer removes when the removal changes the block's text (a `<script>` or `<style>`
     inside a tag goes with its text) or its element count (a `<style>`, an `<iframe>` or a form control between two
     `<p>`s), so the block's source parses to other elements or other text than the sanitizer kept (pane 900,
     `<div>Caption text <script>alert(1)</script> after.</div>` after paragraph 40: no write, the browser's landing on
     paragraph 36 at -51, back +201.5 for -2.5; a `<label>` inside a tag, its text kept, or an `<iframe>` inside one,
     no text, is trusted: Raw on the tag's own row, back -2.5); (4) a hex character reference with no digits (`&#x;`,
     `&#X;`), which Chromium decodes to U+FFFD when its fast-path parser reads a short string of simple tags (the
     block's source alone, as DOMParser sees it) and keeps as the literal when its full parser reads it, which the
     sanitizer's whole-document parse is whenever the note holds a heading, a code block, emphasis or a picture, so
     the two sides disagree on that one form in nearly every note (the same numbers as (3); `&mdash;` in the same
     shape seats); every other entity form, valid or not, decodes alike on both sides. (3) and (4) are malformed
     input, measured by the review's probe over the real viewer and recorded here rather than pinned; the body's
     landing is the browser's own. The edits leg lands after the wrapper both ways (its first scene can be tightened
     to exact once the map pairs the wrapper to its own element); file-view-place-html-browser.test.ts pins (1) and
     (2) as no scrollTop written by the viewer across the switch (a setter trap on the body), and the accepted shapes
     (inline tags, a line break, the README pair, named entities, an entity with no semicolon or past U+10FFFF) as the
     tag's own Raw row and the return to the tag; file-view-place-wrapper-end-browser.test.ts pins the centred div
     closed last, the same div never closed and `<details open>` closed at the end as no scrollTop written either way,
     and the one-tag html block, the paragraph opening with an inline tag and the one opening with an autolink as
     their own Raw row and the return within 1.5px; file-view-place-blocks.test.ts the same over the stand-in, its
     DOMParser built on the same parser, and codeOf's html `<pre>` exclusion (null; a fenced block skip 1, an indented
     block skip 0).
   - *Where it runs.* renderBody reads the place against the text the body was PAINTED from (`shownText`: a reload
     has put the new bytes in `text` before the swap), swaps, runs the seam's hooks, then seats, the order the #348
     selection keeper set (hooks first, then the restore), so the panel's paint pass has run before the body moves
     and the margin lock hears one scroll event. The seam's reload and setMode, the Rendered and Raw buttons and
     openUrlView's own renderBody all go through it, and so does the SVG Source view's paint: the highlighted XML
     is a text view, so it reads, swaps, runs the hooks, records the XML as the text painted and seats, and the
     media paint after it records no text (the Slice 2 review, over 5c0c737c: a reload under the Source view left the
     numeric scrollTop over forty new rows, row 173 at the edge for row 200, and the Comments panel's close moved
     the top row by a row). file-view-place.test.ts pins the order in file-view.ts, file-view-place-svg-source.test.ts
     the Source view's; md-url-view.test.ts pins it in openUrlView's renderBody, the seat between the paint and the
     fragment landing; file-view-place-svg-source-browser.test.ts measures the Source view's reload and toggle.
   - *What a paint costs.* The seat reads the anchor map's block table, so every paint of a text view builds the
     rendered index for the new root, panel or no panel; at 5,000 paragraphs (a 1.2 MB note) a fresh root cost 147 ms
     (the lex 48, the walk over the tokens about 70, the pairing of blocks to elements about 22) and the Raw rows 35,
     so the Rendered click reached its frame about 155 ms after the base's, at pane 900 and 380 alike (the Raw click
     within noise; the scroll frames unchanged, the per-frame read being a cache hit). The source half of the index
     (the normalized text, the placed tokens, the block table and each block's walk) is kept for the last source
     (anchor-map.ts sourceTable, one entry keyed on the text), so a fresh root over unchanged text (a view switch, a
     reload of the same bytes) pays the pairing alone, 22 ms, and the Rendered click reaches its frame 20 to 40 ms
     after the base's (pane 900: base 574 to 586 ms, before the cache 730 to 744, after it 594 to 602; pane 380: 577
     to 586, 722 to 748, 622 to 626; medians of seven clicks, interleaved runs), and a reload of the same bytes under
     Rendered paints within 30 ms of the base's (565 and 558 ms for 561 and 532; before the cache 679 to 726; the Raw
     reload's 35 ms row check stands, being the rows' own). The first paint of new text (an open, a reload after a
     write) still lexes and walks it, once: 93 ms for the root over a 43 ms block table, where the table and the index
     each lexed before. The walk waits for the first Rendered root, so a Raw view (any non-markdown file, whose text
     the block table lexes as markdown once) pays the lex alone, as before.
     file-view-place-source-cache.test.ts counts one Lexer.lex across the block table and three roots over one source
     (four before the cache) and pins the pairing as each root's own: a root whose text mismatches the file refuses
     its block and a fresh root over the same source maps it still.
   - *Numbers.* The same at 380 and 900px: a reload inserting twenty paragraphs above paragraph 40 kept it at the
     top (before: paragraph 28 at 900px, 29 at 380px), in the Raw view too and with the aside open (the margin
     layout); the Rendered, Raw, Rendered round trip came back to paragraph 40 at the same height, pane 900
     scrollTop 1918, 2854, 1918 (before: 1918, 2566, 2566 with paragraph 53 on top), pane 380 5163, 5662, 5163
     (before: paragraph 45), chat 900 2729, 2854, 2729 (before: paragraph 53). file-view-place-browser.test.ts
     measures each over the real module and the real panel; file-view-place.test.ts runs the pure parts (the
     search, the follow, the block table's reads and the Raw span over the anchor-map suite's DOM stand-in).

3. *The round trip returns to the passage, not the scrollTop.* The text asks for the same scrollTop; the Raw view is
   the taller of the two (monospace rows, a row per blank line), so one scrollTop is two passages. The leg asserts the
   passage at the same height, the Raw scrollTop larger than the Rendered one, and the Rendered scrollTop back on the
   return (the numbers in item 2).
4. *The width reflow and a text-size step keep the place too* (beyond the text, which names the swap alone). The
   panel's toggle moved the reader through the width alone: at 900px closing the aside took the body from 560 to 900px
   wide, the scrollHeight from 9138 to 4860, and with the scrollTop kept at 3541 the top block from paragraph 40 to
   73; a pane drag does the same. The ResizeObserver repaint (file-view.ts) now seats the place after
   fireRenderedKeepingSelection. It cannot read the place itself: the observer reports after the layout has changed,
   so the place is read again off the body's scroll event, once per animation frame, and the repaint seats the place
   read before the width moved. A scroll event under a body width the last read did not see is the browser's own,
   its anchoring adjustment or its clamp, and is skipped: read as the place, it already stands in the new layout, so
   the repaint's seat moved nothing and the depth into the top block held in pixels on the aside's open, while the
   close, whose padding write suppresses the anchoring, applied the fraction, so each toggle halved the depth and a
   picture the reader was two thirds into went wholly above the edge (the Slice 2 review); skipped, the repaint seats
   the pre-reflow place and the fraction holds both ways and across a pane drag. One scroll in that window is made on
   purpose and must not be undone: the panel's reveal mounts the aside and centers the mark in one task, and the
   repaint used to seat the pre-click place over it. The viewer sees that width change made: the seam's aside hook,
   the one place a toggle changes the width, reads the body's scrollTop after the mount (the new width laid out, the
   browser's adjustment in it) and keeps the number; a scroll under the new width reporting that number is the
   adjustment the hook saw and is skipped, one reporting another number is the reveal's or the reader's and is read,
   unless it is the clamp (the body at its end, reached from above it, which nothing does on purpose). Under a width
   change no hook saw (a pane drag, the window resized) nothing scrolls on purpose in the same task, and every scroll
   before the repaint is skipped. An earlier rule told the anchoring by a signature, the kept block's top edge within
   a pixel of where it stood, which holds for a paragraph, a picture or a code block and not for a table, a list or a
   blockquote, where the browser anchors on a row, an item or an inner paragraph and the content above it inside the
   block rewraps: a 40-row table walked two rows up per toggle (0.4, 0.35, 0.298, 0.243 of its height), a 40-item
   list 0.4 to 0.422, a 12-paragraph blockquote 0.4 to 0.412, and a drag held the table's pixels (0.35 at 600px)
   where a paragraph held the fraction. The hook's number is exact whatever the browser anchored on, at one layout
   per toggle, which the panel's own measurements force in the same task anyway. A text-size step reads the place
   before applyTextSize and seats after the hooks. file-view-place-reveal-browser.test.ts drives the reveal (pane
   900, chat 1000), a width change no hook saw (a script's scroll to paragraph 70 as the page narrows: paragraph 40,
   the place read before, is seated) and the clamp on the aside's close. file-view-place-browser.test.ts: paragraph
   40 stays the top block as the aside opens (body 900 to 560), closes (back to 900, scrollTop 1918 again), the
   viewport goes to 600 and back, and after A+; a place the reader scrolled to after one reflow is the one the next
   reflow keeps; a reader 80px into paragraph 44 keeps the fraction across three toggles, a viewport drag both ways
   (600, 900, 600, 900) and two thirds into a sized picture (the fifth scene; red before the fix at the first open,
   -39.7 against -79.7); and 0.4 into the table, the list and the blockquote across three toggles and a drag (the
   sixth scene; red before this rule at the first open, 0.35 of the table's height).

5. *No `overflow-anchor: none`.* The text asks for it. The gap analysis showed the base behaviour was never
   anchoring's doing: the swap removes the anchor node and Chromium keeps the numeric scrollTop with `auto` and `none`
   alike (1918 to 1918 either way), and after a restore anchoring helps: a 200px growth above the kept block (a figure
   landing late) left the block in place under `auto` (scrollTop 2471 to 2671, the block at the same height) and
   pushed it down under `none` (the top block became paragraph 36 at 900px, 38 at 380px). Not every swap: where the
   anchoring can re-find an anchor in the new content it moves the body with it (the Slice 2 review, over 5c0c737c: a
   swap the viewer left alone with the reader 3px into an html block, 1969 to 2617, no write of the viewer's, the
   number standing under `none`), which is why the refusals of item 2 are pinned as no write, not as a number. The
   sheets declare nothing; file-view-place.test.ts pins the absence.
6. *A sized picture keeps its ratio.* `img` joined the pixel-sized media rule of Slice 1's build note 5:
   `:where(.fileview-md :is(img, svg, canvas, video)[width]:not([width$="%"])) { height: auto; }`, byte-equal in both
   sheets (fileview-parity.test.ts's head moved with it, file-view-text-size.test.ts's declaration pin too). Before,
   `<img width="900" height="300">` laid out 344 by 300 in a 380px pane (ratio 1.15) and 860 by 300 under the measure
   at 900 and 1200px (2.87), the height attribute holding while the cap took the width, so every picture wider than
   the measure was squashed at every width; now 344 by 115 and 860 by 287. Not `height: auto` on `.fileview-md img`:
   that grew `<img width="100%" height="30">` from 30 to 115 and 287px and a height-only badge from 300 by 100 to the
   full column, the two guard cases the svg and video rule met in Slice 1. A picture whose attributes lie about its
   bytes (300 by 300 declared over a 900 by 300 file) follows the bytes (300 by 100), as an attribute-less picture
   does and as GitHub shows it. md-sanitize-wide-media-browser.test.ts lays the three picture shapes, the two guards
   and the lying attributes out at 900 and 380px, after every picture has decoded.
   file-comments-regions-browser.test.ts carries the rule too and lays the README shape (600 by 400 at the picture's
   ratio) and a height-only picture the guard leaves stretched (600 by 800) out with the region layer over them, the
   overlay the element in both (it had pinned the 600 by 800 element for the README shape, which the sheet no longer
   produces).
7. *The note bar above the body row.* noteBar prepended `#fileview-save-err` into `.fileview-body`, so it scrolled
   away with the text (at scrollTop 400 it sat 400px above the body's top), went with every body.replaceChildren (a
   view switch, a reload), and the "past the end" notice scrollToLine raises was never seen: the landing scrolled the
   last row into view after the notice was prepended, leaving it 6732px above the body's top. The bar is now a child
   of the card between the title bar and `.fileview-main` (`box.insertBefore(bar2, main)`; `.fileview > .fileview-err
   { flex: 0 0 auto; }` in both sheets, in the parity list), in openFileView and, through the same noteBar, the
   fallback editor's notice, which built its own bar before. It shows at any scroll position and outlives every swap;
   the editor's entry and exit remove it themselves (enterEdit, exitEdit), which the body swap did for them before: a
   refusal since lifted goes as the editor takes the body, and the edit's notices go with the editor, with the
   comments-log warning raised again after the exit as before (noteLog). file-view-notebar-browser.test.ts drives both
   notices in the pane and in the chat modal: the past-the-end notice above the row, in the card and on screen at the
   landing and at scrollTop 400, still there after the Rendered and Raw swaps; the Edit refusal above the row at
   scrollTop 1500 with the body unmoved, a second notice replacing the first, and still there after a reload. The pins
   that read the notice under the body moved to the card: styles-fileview-err-sizes, file-edit, file-view-seam,
   file-view-edit-races, file-view-undo-landed and -ack, file-view-edit-events, file-view-tracked-edit,
   file-view-links-browser (its stand-in bar mounts where the bar does).
8. *The Comment float hides on the body's scroll.* file-comments.ts hideFloatOnScroll, installed in the panel's
   constructor with the float's other listeners (a passive scroll listener on the viewer's body, removed at dispose),
   not among installLayout's scroll listeners: those feed the margin lock's mirrorScroll, which returns early unless
   the aside is open in the margin layout, and the float must hide in every layout (installLayout itself runs from the
   same constructor for every layout). The margin lock's own write of the body's scrollTop (a wheel over the cards
   track, mirrored) fires the same event and hides the float too: the passage has moved under the reader just the
   same; the leg states it. The selection stands, and the next mouseup offers the button again. One body scroll moves
   nothing on screen: when an unsized figure above the viewport lands its bytes, Chromium's anchoring grows scrollTop
   by its height so the text stays put and fires a scroll event for the write; the Slice 2 review found the float
   hidden on it, the selection within a pixel of where it was, so the listener now compares the subject's rect
   (the live selection's last range, or the picture's box) with the one the button was offered beside (showFloat
   records floatAt; hideFloat clears it with the float) and keeps the float while the passage sits within a pixel of
   it. The same figure landing inside the viewport, above the passage, moves the passage down by its height with no
   scroll event at all (anchoring adjusts for growth above its anchor node alone), so the listener runs on a figure's
   load too, heard on the body in the capture phase since load does not bubble, and the same comparison hides the
   float (the Slice 2 review, over 5c0c737c: the button stood some 300px above the passage it was offered beside,
   pane 335px and chat 304px, and a click on it commented on text the reader could not see under it; not a regression,
   the base does the same). file-view-float-anchoring-browser.test.ts holds the picture's request until the float is
   up and then releases it: the first scene with the picture above the viewport (pane 900 at paragraphs 3 and 30, chat
   900; red over ebdc57b5), the second with it inside the viewport above the selection (pane and chat 900; red over
   5c0c737c); file-comments.test.ts pins the listener beside the scroll one and its removal.
   file-comments-float-scroll-browser.test.ts, over the real panel, in the list layout (380px) and the margin layout
   (900px), and the track's mirrored scroll. Two things the leg met in Chromium and works around, neither the
   viewer's: a selection drag that starts on the body's top line autoscrolls the body, and a mousedown on selected
   text starts a drag of that text, not a selection.
9. *The container-type cleanup.* `.fileview-main` no longer declares `container-type: inline-size`, in both sheets:
   the card declares it (item 1), and a query styles a container's descendants, never the container. The aside's rule
   inside the query resolved against the row before and resolves against the card now, and it reads the same number
   either way: a size query measures its container's CONTENT box, and the row is exactly that box (the card's 1px
   borders in the modals lie outside it, neither the card nor the row has padding, and the pane strips the border), so
   the fold's two rules always flipped together, in the chat and feed modals between viewports 717 and 718 (card
   681.14 then 682.09px wide, row 679.14 then 680.09, the query `max-width: 680px`). The declaration was redundant,
   not a defect, and its removal changes no layout number. An earlier draft of this note named a 2px band of card
   widths (681 and 682px) where the row stayed unstacked while the aside took 45% of it; the review's probe over the
   base commit's sources with the real panel open (chat and feed at 380, 640, 700, 714 to 720 and 900px; the pane at
   380, 640, 679 to 683 and 900) found the two rules agreeing in every cell, on the base tree and on this one, so
   there was no such band. Which box the aside's rule read was the only thing the cleanup changed.
   file-view-fold-browser.test.ts replaces the CSS-text match at file-comments.test.ts:879 (the plan's :854): the
   Files pane and the chat modal at 380, 640 and 900px with the real panel open, the row a column and the body and
   aside the row's whole width with the aside below at the two narrow widths, two columns at 900, the card
   `inline-size` and the row `normal`. Before the cleanup the row's `container-type` read `inline-size` and nothing
   else in the leg differed.
10. *Tests and infrastructure.* The thirteen legs (file-view-place-browser, file-view-notebar-browser,
    file-comments-float-scroll-browser, file-view-fold-browser, and the review's file-view-place-blocks-browser,
    file-view-place-reveal-browser, file-view-place-edits-browser, file-view-float-anchoring-browser,
    file-view-leg-page-browser, file-view-place-float-browser, file-view-place-html-browser,
    file-view-place-svg-source-browser and file-view-place-wrapper-end-browser) share one test-only page module,
    `ui/webview/real-viewer-leg.ts` (the viewer bundled from the tree, a fetch answering the file route from an
    editable table, an .svg served as an image with the kernel's Content-Type, a poster answering the panel's status
    ask so the real aside opens on a click, a probe action counting the seam's paints), instead of thirteen copies of
    the same eighty lines; a leg runs over another tree from that tree's vscode-extension (the cwd names the tree, as
    for every browser leg), which is how each leg was run over a copy of the base commit's sources and shown red there
    (place 4 of 4 scenes, note bar 2 of 2, float 2 of 2, fold on the row's container-type; the review's blocks leg 6
    of 7 and reveal leg 1 of 2 over the same copy: its two green scenes, the scrollTop 0 round trip and the reveal
    left centered by the width reflow's repaint, pin regressions of the build's own mechanism that the review fixed,
    not defects of the base, which keeps the numeric scrollTop, so 0 stays 0, and has no reflow seat to undo the
    reveal; over the build's own tree, 63a8c4e4, the legs are 0 of 7 and 0 of 2; the review's later legs over the
    tree after its first fixes, ebdc57b5: edits 0 of 4, float anchoring 0 of 1, the place leg's fifth scene red at
    the first open, the leg page 0 of 2; over the tree after its second fixes, 5c0c737c: the html leg 0 of 6, the
    SVG Source leg 0 of 2, the float anchoring leg's second scene, the place leg's sixth scene and the reveal leg's
    second test red, and the floated-figure leg 0 of 1 over that tree with topVisibleIndex's pass-over removed,
    where the Raw switch lands on the `<img` row at scrollTop 338 for 464 and a reload drops the passage 40px; over
    the base the same leg's Raw assertion is red too, the numeric scrollTop showing paragraph 4 in the pane and the
    `<img` row in the chat; over the tree after its third fixes, 66368710: the wrapper-end leg 1 of 3, the Raw switch
    from the nested paragraph writing scrollTop 2934.6 on the div closed last and the reverse switch 2073, the
    controls green; and the html leg's wrapped-line scene, which since the fourth round runs its two pane drags twice,
    with the browser's scroll anchoring on and then off, is red over the base on the anchoring-off pass alone, the
    character at -2502 for -20.4 with no write, since with anchoring on Chromium holds the character within 0.2px and
    the seat's delta falls under its half-pixel threshold, so that pass pins the point the seat computes and the other
    the seat's presence). The page writes
    every value it inlines into its script with `<` as `\u003c` (scriptLiteral), since an HTML tokenizer ends script
    data at the first `</script` whatever the JavaScript around it: a fixture holding one cut the harness script off
    before the fetch stub, and the viewer fetched the harness page itself as the note
    (file-view-leg-page-browser.test.ts, 2 tests). No environment variable redirects the tree: one did, and a value
    left in a shell would have run the legs over another tree than the rest of the suite with nothing in the output
    saying so (file-view-leg-tree.test.ts pins its absence). The legs await frames and paint counts, never a timer.
    docs/guide.md's Files section gained the sentences for each rule.


### Slice 3: a document type scale

A GitHub heading scale, h5 and h6 dimmed at 1em, h1 and h2 ruled; a `--font-doc` token (decision 3);
2em list gutter; bullet-less task items with `accent-color` and `color-scheme`; th weight 600,
`--overlay-05` fill, even-row striping; `[align]` honoured; `<kbd>` styling; `tab-size: 4`; an
`@media print` block; the chat's `wrapCodeLines` and `addCopyBtn` shared with mdBlock, plus decision
5's grammars; the reading measure of decision 4, a centred column near 80ch at about 15px that
`--fv-scale` (fork PR #348) scales. Acceptance: h1 to h4 compute 2, 1.5, 1.25 and 1em; the prose
column is centred in the body and measures about 80ch at 100 percent; a task item computes `list-style:
none`; a `:---:` column computes `text-align: center`; `--hl-cmt` on the code background measures
4.5:1 or more; a long note prints multi-page in black; every fence has a gutter and Copy;
anchor-map paints across `.cl` spans. Tests: computed-style leg; wrapped-code anchor-map fixture.

**The Slice 3 build** (2026-09-08). Branch `mdviewer-s3`, stacked on `mdviewer-s2` (5c0c737c) with the fork's main
merged in (aa474a3e), and again at 461c6f76 once Slice 2 had landed as fork PR #396. The gap analysis behind it ran
every criterion above in headless Chromium over the real viewer at the Slice 2 tip; the numbers below are its and the
build's. Where the code as built departs from the text, why, and which test holds each rule:
1. *The heading scale.* GitHub's: h1 2em, h2 1.5em, h3 1.25em, h4 1em, h5 and h6 1em in the dim tier, weight 600, a
   1px rule under h1 and h2 with 0.3em of padding above it, em of the prose so the text-size control scales them. The
   text names no margins. GitHub writes its in rem, 1.5 above and 1 below every heading whatever its size; here the
   distance is 1.5 prose-em above and 0.5 below, the larger levels dividing by their own size to land on the same
   distance (`calc(1.5em / 2)` on h1), and the first child of the note stays flush. Before: h1 16.9px, h2 14.95, h3
   13.65, h4 13 (equal to strong), h5 10.79 and h6 8.71 in bold from the browser's own sheet, no rules. After, at 100
   percent: 29.9, 22.425, 18.6875, 14.95, 14.95 and 14.95 dimmed; at 115 percent 34.385, 25.79, 21.49, 17.19.
   file-view-typescale-browser.test.ts measures the six levels, the rules and the margins on the three surfaces at
   both sizes and in both themes; file-view-text-size.test.ts and styles-fc-region-layer.test.ts re-pin the h1 at 2em.
2. *Decision 3: the `--font-doc` token.* Declared in all four token blocks (styles.css and feed.css, `:root` and
   `body.theme-light`), `var(--sans)` in both themes, and `.fileview-md` reads it; `--font-prose` is untouched and
   still mono in light for the chat's replies. A `--color-scheme` token (dark, light) joins it in the four blocks so a
   form control a note carries is drawn for the theme (item 5). The `.fc-overlay` reset that stopped the light theme's
   mono face reaching a figure's chip has nothing to stop on the face now and stays for the size, which the 2em h1
   makes more necessary; its comment and the region-layer leg's light-theme assertion say so. The typescale leg reads
   the note's computed face in light (Space Grotesk, the body's) and `--font-prose` still resolving to the mono stack
   there.
3. *Decision 4: the measure.* The prose is `calc(var(--fs) * 1.15 * var(--fv-scale, 1))`, 14.95px at the 13px default,
   so the note follows `--fs` (13px on every surface today: VS Code hands a webview no chat font size variable, the
   review's round 2) and the control still scales it; fenced code stays at 12px times the scale.
   The column is the root's own inline padding, `max(18px, round(down, calc((100% - 80ch) / 2), 1px))`, so it is
   eighty of the root's own zero glyphs, centred in the body, at every size and in either face, and every child of the
   note sits in it, pictures and the figure layer's wrapper included; the 860px cap on every block (`.fileview-md >
   :where(:not(table))`) and the direct-child media cap that scaled it are gone. The text says about 80ch; the build
   is exactly 80ch rounded up to at most two pixels: the padding is rounded DOWN to whole pixels, since a fractional
   left edge (69.84px at 900) put the text on sub-pixel positions where headless Chromium's drag selection stayed
   collapsed at some offsets (4px into the first glyph at 70 percent, 5 and 12px at 100; measured 2026-09-08, and gone
   with an integer edge), and whole pixels keep the two gaps equal to the pixel. Before: 860px, left-pinned, 104 zero
   glyphs. After: 760.3px is 80.0ch at 900 and 1400 (ch 9.5px), 762px with the rounding; at 115 percent 80ch is 875px
   and a 900px pane caps the column at 864 (79ch); at 380, 344px (36ch). A plain `padding: 14px 18px` stands before
   the rounded declaration as the fallback for a browser without `round()`. The chat's own `.md` scale is not touched.
   The typescale leg asserts the column against the glyph width and the two gaps within a pixel at 900 and 1400, the
   aside open and closed; file-view-text-size.test.ts's declaration pins and its 860 numbers were rewritten, and its
   one drag now starts 2px into the paragraph instead of 4 (the quirk above).
4. *The pane-wide table under the centred column.* A table of the note's own (`.fileview-md > table`) is capped at the
   BODY's width less the root's inset, not the column's: `calc(var(--fv-body-w, calc(100% + 36px)) - 36px)`, where
   `--fv-body-w` is the body's content width, written on `.fileview-body` by the width observer file-view.ts already
   runs for the reflow (the ResizeObserver's report is the layout's own event; one write per report), and `max-width:
   100%` on every table is the cap for one inside a quote or a list item, the guide's standing promise. The formula
   first proposed for the centring (`margin-inline: calc((100% - 100cqi) / 2)`) was not used: a block with negative
   inline margins starts at its left margin edge, so a narrow table would have sat at the body's edge, left of the
   prose. The table is instead moved by `translate: min(0px, round(calc(<half the body> - <the padding> - 50%),
   1px))`, a percentage in translate being of the table's own width: a table no wider than the column is not moved
   and sits at the column's left edge with the prose, as on GitHub, and a wider one is moved left by half of what it
   exceeds the column by, so it grows out of the column evenly into both gutters until it meets the body's inset, and
   scrolls in its own box past that. The table's layout box stays where the layout put it, so the body never scrolls
   sideways (`contain: layout` on the root). Before the observer's first report, or without one, both declarations
   read the same stand-in, 100% plus the inset the cap takes back: the cap is then the column and the shift exactly
   none (the padding term rounds down to its 18px floor for any table the column holds), so the table sits at the
   column's left edge, as it does in a browser without `round()`. `display: grid` on the table, the other way to
   centre a box by its own width, was tried and rejected: Chromium blockifies thead and tbody into separate items and
   the columns no longer align. Measured at a 1400px pane: a six-column table 1207.9px wide in a 762px column with
   gaps of 96.0 and 96.1px; a fourteen-column table 1364px, from inset to inset, scrolling 2596px inside it; with the
   Comments aside open (body 1060) the same tables 1024px, the body's, not the card's; at 900, capped at 864; at 380,
   the column's 344. The typescale leg's second test lays the three tables out at 380, 900 and 1400 on the three
   surfaces, the aside open and closed; file-view-text-size.test.ts pins the declarations and the observer's write,
   file-comments.test.ts the body's rule. The table's `scrollWidth` can read one pixel over its `clientWidth` when its
   max-content width lands a fraction over the cap (913 in 912 at the document size); that check carries the pixel of
   slack the code block's already had. The cap was a container unit first (`container-type: inline-size` on the body,
   `calc(100cqi - 36px)`), and the review's two rounds moved it off: a container unit resolves against the box BEFORE
   an `overflow: auto` scrollbar takes its space, while the root's 100% padding resolves against the content box after
   it, so on every note that scrolled the cap and the column disagreed by the scrollbar's width and a pane-wide table
   sat 8px from the pane's 10px scrollbar (round 1); `scrollbar-gutter: stable` made the two agree and reserved a
   blank strip on every body that never scrolls, a short note 5px off the card's centre, a picture too, a PDF frame
   and the editor 10px short of the body's edge, 15 on the feed's platform scrollbar (round 2). The observer's width
   is the content box the column is measured in, scrollbar or none. The other legs never saw the scrollbar, since
   playwright launches Chromium with `--hide-scrollbars`; file-view-scrollbar-browser.test.ts launches without that
   flag and measures `--fv-body-w` against the body's client width and the table 18px from both edges at 380, 900 and
   1400, the aside open and closed, and that nothing is reserved beside a note that does not scroll, a picture, the
   PDF frame or the editor.
5. *Lists and tasks.* `padding-left: 2em` on ul and ol (was 1.4em). mdBlock stamps GitHub's `task-list-item` on a list
   item after the sanitize when its first child is a disabled checkbox, or the first child of its first paragraph is
   (marked puts a loose list's box inside the paragraph; the text names the first child alone); the item computes
   `list-style: none`, and the box wears `color-scheme: var(--color-scheme)`, an explicit 13px box, the prose's font
   size (`font-size: inherit`, in a rule of its own: the geometry rule's attribute and :first-child selectors are
   outside the grammar the sheet's font-size rules keep, styles-fc-inline-chip.test.ts) and `margin: 0 0.2em 0.25em
   calc(-13px - 0.46em)` into the gutter, fitted to Chromium's disc, whose centre sits about 7px plus 0.45em before
   the item's text at every size: GitHub's -1.4em in the control's own 13.33px em sat the box 5px off the sibling
   bullets at 150 percent, and the fit's stagger is under 1px from 70 to 200 percent and at the 11 and 16px chat sizes
   (the review, round 1). No `accent-color`: the sanitizer keeps every box disabled and Chromium paints a disabled box
   grey whatever accent is declared, so the text's declaration was inert. The typescale leg checks both list shapes,
   the plain item's kept bullet, the scheme, the box's font size equal to the prose's and `accent-color` at `auto`.
6. *Tables.* th weight 600 on `var(--overlay-05)` (was 700 on `--box-bg`, 1.09:1 against a cell), even body rows on
   the same wash, and `[align="center"]`, `[align="right"]` and `[align="left"]` rules for th and td, since the shared
   `text-align: left` outranked the attribute marked writes for a `:---:` column. Both sheets' th rules are byte-equal
   now (feed.css carried a fallback for `--box-bg`, which its `:root` lacks; `--overlay-05` it has). The typescale leg
   reads the weight, the fills and the three alignments.
7. *kbd and tabs.* `.fileview-md kbd` on `--kbd-bg` and `--kbd-border` (the settings modal's tokens, in both sheets),
   mono at the ladder's 0.86em, a 3px radius, an inset bottom shadow line. `tab-size: 4` on `.fileview-md pre code`,
   the Raw view's value (was the browser's 8). The typescale leg reads both on every fence.
8. *Fenced code shares the chat's dress.* `ui/webview/code-block.ts` holds `wrapLinesHtml` (the pure walk),
   `wrapCodeLines`, `addCopyBtn` and `copyText`, moved from render.ts as they were; render.ts and file-view.ts import
   them, and file-view.ts still imports nothing from render.ts. mdBlock captures the raw text first, highlights a
   fence that names a registered language (never `highlightAuto`), then wraps EVERY fence in rows and gives it Copy,
   named or not; the math fill's source fallback keeps Copy alone, as in the chat. The line counter resets on
   `.fileview-md pre code` rather than `code.hljs`, since a plain fence carries no hljs class and would have gone on
   counting. Scoped copies of the chat's `.cl`, `.ct`, `.has-copy` and `.code-copy` rules sit in both sheets,
   byte-equal, the code tint with the chat's literal as its fallback (feed.css defines no `--code-bg` in `:root`).
   code-block.test.ts runs the walk and pins the callers, the bundle boundary and the sheets; codeblock-copy.test.ts,
   codeblock-wrap.test.ts and file-view.test.ts point at the module; the typescale leg counts rows and Copy on a
   python, a rust, a zig and an unnamed fence. The viewer's link pass (file-view-links.ts) joins the text nodes under
   the nearest line unit, and a wrapped fence's `pre` no longer holds newlines, so `.cl` joined `.fv-cl` in
   LINE_UNITS: without it a path ending one line ran into the path beginning the next (`data/x.jsondocs/fence2.md`),
   and file-view-links-browser.test.ts caught it. From the review: the gutter rule, the chat's and the viewer's copies
   alike, is `flex: 0 0 max(2.5em, calc(var(--ln-digits, 0) * 1ch + 0.05em)); line-height: 1; overflow-wrap: normal`.
   At 0.92em under `align-items: baseline` the number's line box hung further below the shared baseline than the
   text's, so every row was 18.5625px against an 18px line-height (the fraction that crept the kept code line a pixel
   per Rendered/Raw round trip at 380px and beside the aside), and a four-digit number broke over two lines in the
   2.3em basis and doubled every row from line 1000 on (round 1). With `line-height: 1` on the gutter a BLANK line's
   row fell to the gutter's own 11px, an empty `.ct` having no line box, and a blank line inside a token that spans
   lines (a docstring's) the same, its `.ct` holding an empty hljs span; and a five-digit number widened its own row's
   gutter alone (a flex item's min-content), stepping the text 5.6px right from line 10000 on (round 2). Now the
   `.ct`'s `::before` is a word joiner (U+2060: zero width, no break before or after it, outside the DOM's text and
   any selection), so an empty `.ct` is one line-height with the text's baseline and a text line is unchanged (a
   no-break space on `:empty` missed the spanned blank line; a zero-width space and an inline-block each broke an
   over-long line once more); and wrapCodeLines writes `--ln-digits`, the digits of the fence's last line number, on
   the code element, so every row of a 10000-line fence shares a five-digit gutter (a pure-CSS `:has()` on the ten
   thousandth row was built and rejected on measured cost: the one-shot layout of a 10005-row fence went from 269 to
   1617ms and a 1200-row fence from 41 to 235ms, a price every chat fence would pay).
   file-view-fence-rows-browser.test.ts measures a 1200-line fence's rows with twelve blank lines, the blank shapes in
   a python and an unnamed fence at 100 and 150 percent on the pane and the feed, a real 10005-line fence's gutter,
   and three round trips at three widths on rows over text and under one and two blank rows. Copy copies the fence's
   text as the note holds it: marked's lexer turns a line's leading tabs into four spaces each before it cuts the
   fence, so the raw text mdBlock captured pasted a Makefile recipe back as spaces. fence-source.ts finds each code
   token's lines in marked's view of the source and reads them back (a fully expanded tab is a tab again, one a list
   item's indent consumed part of is the spaces CommonMark leaves, a mid-line tab was never expanded, and an empty
   fence, whose text marked also gives a fence of one blank line, is matched by its opener and closer rather than
   searched as one blank line, which had claimed the blank first line of the next fence and cost that fence its tabs:
   round 2), and mdBlock hands addCopyBtn the note's bytes for every document kind, the rendered text for a fence it
   does not find (file-view-fence-source.test.ts over the real marked; file-view-copy-source-browser.test.ts on the
   pane and the feed). And the button's label is not the note's text: anchor-map's text walks skip the `.code-copy`
   control, since the label had joined a block's rendered text and every block holding a fence, and every list or
   quote with one in it, was refused as not matching the file (file-view-copy-map-browser.test.ts).
9. *The anchor map across rows.* The wrap drops the newline each row stands for, so a wrapped code element's
   textContent runs its lines together, and paintRendered's fallback matched a quote holding a newline against a hay
   reading "commentdef" (0 marks for a two-line comment range, where the unwrapped block painted 13). anchor-map.ts
   now reads a code element's lines through one set of helpers, `codeRuns` (the text runs with a newline put back
   between adjacent `.cl` or `.fv-cl` rows) and `codeText`, with `codeLineAt` and `codeLineStart` beside them; the
   fallback builds its hay from `codeRuns` and maps the hit back onto the text nodes, and reader-place.ts reads the
   code line at the body's top edge and where a line starts off the `.cl` rows themselves, as it reads the Raw rows
   (the first row whose box ends below the edge, its index the line number, its box's top the line's top). Round 1
   read them through the browser's hit test at the first `.ct`'s left edge and `codeLineAt` over the DOM position (the
   end of one row's text and the start of the next are one offset and two lines once the newline is gone); round 2
   found that a blank line's row holds no character, so the hit test read no line and the seat fell to the block
   fraction, that a Range around the empty row read back a zero-height rect at its baseline, 9px under the row's top,
   and that a text row read at its glyph's top, 2px under the row's, so a code row at the edge came back 14 to 17px
   off after a Rendered/Raw round trip, walking on some trips (file-view-fence-blank-rows-browser.test.ts: a blank
   row, rows under one and two blank rows, four cells, three trips each, exact). Round 3 of the review found the hit
   test kept for a code element with no rows unreachable: its stated case, the math fill's source fallback, opens with
   `$$` or `\[` and is no code block to codeOf, and every fence and indented block mdBlock builds has rows; the branch
   went with caretAt, charTop and reader-place's codeLineAt and codeLineStart imports, so a code element with no rows
   keeps the depth rule (file-view-place-blocks.test.ts pins the rowless read over a document that offers a hit test,
   and codeOf's refusal of a `$$` or `\[` block). anchor-map's `codeLineAt` and `codeLineStart` stay, exported for
   Slice 8's exact code-line mapping; nothing in production calls them today (the final fixes after round 3:
   anchor-map-wrapped-code.test.ts exercises them and pins that no production module calls them, so a caller added
   later updates this sentence and anchor-map.ts's header). After: the two-line range paints marks in rows 0 and 1,
   the whole fence in its four text rows, a two-line range of a plain fence in both rows, an insertion across lines in
   two or more rows, and a Rendered selection inside code is still refused with the Raw offer.
   anchor-map-wrapped-code.test.ts (node, over a stand-in built from the walk's own output) and
   anchor-map-wrapped-code-browser.test.ts (the real files bundle over anchor-map-fixtures/fenced.md) hold it; the
   Slice 2 place suites are unchanged and green.
10. *Decision 5's grammars.* `ui/webview/viewer-grammars.ts` registers rust (rs), go (golang), c (h), java, sql and
    ini under both `ini` and `toml` (hljs 11 has no toml module; ini.js declares the alias), and file-view.ts imports
    it, so files.js and feed.js gain them through the viewer and the chat bundle through file-view.ts. The chat's
    auto-detection of an unlabeled fence keeps to its ten: highlight-cache.ts passes `AUTO_LANGUAGES`, the ten names
    render.ts registers, to `highlightAuto`. Beyond the text: the code view's extension map gains rs, go, c, h, java,
    sql, toml and ini, so a `.rs` file reads as a rust fence does. Bundle deltas against the branch's base, production
    (minifyWhitespace and minifySyntax, identifiers kept, as esbuild.js builds): files.js 466,821 to 491,370 bytes
    (+24,549; gzip +7,641), feed.js 745,735 to 770,404 (+24,669; gzip +7,635), render.js 1,456,132 to 1,479,885
    (+23,753; gzip +7,724); the six grammars are 20,781 of that (sql 7,068; c 4,741; rust 3,229; java 3,099; go 1,425;
    ini 1,219), code-block.ts 1,612 and the anchor-map helpers 1,807, less 882 reader-place.ts gave back.
    code-block.test.ts registers the six in node and pins the subset and the imports.
11. *The code-comment token.* `--hl-cmt` dark from #6f6a5f to #978f81: 2.85:1 on a code block (the fill composited
    over the card) to 4.79:1, 5.21 on the card; light from #6E675C to #67614f: 4.39:1 to 4.86:1. The chat's `.md pre`
    reads the same token, so the chat's code comments are lighter in dark and darker in light too.
    theme-parity.test.ts holds a pair for `--hl-cmt` over `--box-bg` at 4.5 beside the standing 3 over `--bg`; the
    typescale leg measures the ratio from the browser's computed colours in both themes; file-view.test.ts's palette
    pin carries the new values.
12. *Print.* An `@media print` block at the end of styles.css and feed.css, byte-equal, and the pane's own overrides
    in files-pane.css in keywords (no bare hex; css-census stays at 0): the modal's fixed overlay becomes static and
    its 95 percent card unclipped (the pane's viewer keeps the position: relative files.test.ts pins, for the z-index
    it holds on screen; in flow it prints as a block just the same), the page and the card white with black text, code
    tokens and line numbers black, the body's scroll box open, the title bar, aside, Comment float, notice bar and
    Copy buttons hidden, and everything else on the page left out while a note is open
    (`body.fileview-open > :not(#romp-fileview)`). Before: one page, the card's dark grey, on the pane and the chat
    modal. After: ten A4 pages for the gap analysis's 120-paragraph note on both. file-view-print-browser.test.ts
    emulates print media, reads the computed styles with the real aside mounted, counts the PDF's pages, and returns
    to screen media; its node test pins the block byte-equal (fileview-parity's rule reader cannot read a nested
    block). The block also names `a.file-uri-link` (its class outranked the bare anchor rule, so a link to a file kept
    the screen's ink and lost its underline), prints a task box in the light scheme (Chromium paints a dark-scheme
    unchecked box as a filled dark square on white, an open task reading as done), lays a table out as a table again
    with its cells wrapping to the column (paper cannot scroll the screen's block), and prints the comment marks bare
    (`.fc-hl`, `.fc-hl-context`, `.fc-presel`; the comments they point to are left out);
    file-view-print-marks-browser.test.ts measures the five (the review, rounds 1 and 2). The print leg's own `before`
    count is taken with screen media forced, since page.pdf renders under print media by default, so what it counts is
    the defect's rendering, and the leg asserts it at one page (round 2). Round 2 extended the block: code prints
    black wherever it is in the body (the Raw view and a source file are `code.hljs` under `.fileview-pre`, outside
    `.fileview-md`, and `.hljs-title.function_` at two classes outranked the fence rule;
    `.fileview-body code.hljs span` outranks it), a region comment's overlay is left out (its rectangle printed amber,
    and solid white over the figure with backgrounds off), the change marks print black with no wash (a black
    underline, a black struck label, the Raw view's chip black in a black ring: a redline, with Show changes inline
    for a print without them), a framed picture's inline outline (styleFrame in file-comments.ts) is stripped with
    `!important`, the one way a sheet rule outranks an inline declaration, and a table of the page's own keeps the
    body's room and the screen's shift on paper, the cqi cap and translate restated in the block with the body made a
    size container there (the column alone squeezed a 6-column table to 761 of A4 landscape's 1123px, every cell
    broken mid-word); file-view-print-inks-browser.test.ts measures these, and the print leg's fixture is 120
    paragraphs now (it was one 120-line paragraph; 9 A4 pages at the leg's 900x700). Round 3 corrected the block on
    the served pages: its page head is `:root, body.fileview-open`, not `html`, since the kernel's chat and feed pages
    inline THEME_CSS in a `<style>` after the sheet's `<link>` and its `html,body{background:...}` is a type selector
    of the same specificity later in the cascade, so it won the tie under print media and the root, which paints the
    page canvas, printed the editor's dark grey wherever the body did not cover the page (the pane was spared by
    files-pane.css's own print rule, which sits after THEME_CSS in the same style element); `:root` outranks a type
    selector wherever the theme's rule sits. The fence's and the Raw view's line numbers print at opacity 1: the
    screen's 0.32 and 0.55 stood in print, black ink or not, the fence's at 2.24:1 on white. And the print leg's page
    carries THEME_CSS through real-viewer-leg.ts's `theme` option, placed as the kernel places it, which is why the
    leg had passed while the served pages failed; its `htmlBg` assertion fails without the `:root` head, and
    file-view-print-inks-browser.test.ts asserts the gutters' opacity.
13. *Pins moved.* fileview-parity.test.ts gains the new heads (the headings, the list gutter and task item, kbd, the
    fences' rows and Copy, the table's fill, striping, alignment and break-out) and loses the direct-child media cap;
    styles-fc-region-layer.test.ts re-pins the h1 at 2em, the face at `--font-doc` and its control's compounding at
    2.3 times; file-comments.test.ts the body's plain rule (round 2 took `container-type` off the screen body, item 4;
    the print block's is pinned by file-view-print-browser.test.ts); codeblock-copy.test.ts the auto-detection subset;
    the two md-sanitize legs' comments the retired 860px cap. The Slice 2 legs that read the old geometry were
    re-pinned, not loosened: the Rendered view is the taller of the two at 900px now (15px prose in an 80ch column
    against 12px rows at the pane's width), so the round trip's Raw scrollTop is asserted to fall short of the
    Rendered one rather than to exceed it, the bottom-of-document round trip starts in the shorter view (Raw), a
    paragraph that was two lines at 900px is three and the fraction assertions say so, a replacement shorter than what
    showed sits at the edge, the three margin legs and the six margin sheet suites (feed-css-margin-fit, -leader,
    -footers, -footer-rule, styles-fc-margin-fit and -footer) name the six-heading rule head, the whitespace-point
    leg's sentence leaves room beside it for the struck labels in the narrower column, and the place-edits leg's line
    reader reads the `.cl` row under the caret.
14. *The reader's place and the press, from the review (round 1, 2026-09-08).* A seat the browser CLAMPED (the view
    the place is seated in is shorter than the one it was read in, and the body stands at its end) was read back as
    the reader's place, naming the paragraph the clamp shows rather than the reader's, so the Rendered/Raw round trip
    from the end of the taller view came back one paragraph early (65px on the chat at 900; before the slice the Raw
    view was the taller and the same clamp drifted the other way, by up to 264px). reader-place.ts's
    `seatPlaceOutcome` reports the clamp off the write itself (the scrollTop the body took against the one asked),
    `seatPlace` wraps it, and openFileView keeps the place it seated while the body stands where the clamp left it:
    the seat's own scroll event is skipped, and the first scroll that moves the body ends the hold. No timers.
    file-view-place-blocks-browser.test.ts's bottom scene pins both directions on the chat and the pane. Round 3 gave
    openUrlView, the same viewer for a same-origin .md link, the same held place: it read and seated through the plain
    seatPlace and came back a paragraph early from the end of the Rendered view on the chat and 35px off on the pane;
    file-view-url-place-bottom-browser.test.ts pins the chat and the pane from the end of Rendered, the clamped
    direction, and the chat from Raw. And a reload's fetch landing (the Comments panel's poll saw a session's write)
    rebuilds the body under no gesture of the reader's, so a press on a fence's Copy that straddled it lost its click:
    a pressed node removed before the mouseup dispatches no click that names a control (probed with real input events
    in headless Chromium 151 and Firefox 153; delegating the action would not help, and ui/CLAUDE.md's sentence that a
    swapped target still bubbles to the stable ancestor was wrong on this point: round 2 rewrote the rule, delegation
    and the hold named as complementary). The landing is held while a pointer is pressed over the body and runs at the
    release (actions.ts `pressHold`, the timeline's `_pointerHeld` guard as a helper; the landing's own guards re-run
    then). Since round 3 the guards run BEFORE the hold's defer as well (`stands`: the wrap connected and this fetch
    the newest out): the hold parks in defer order and a later defer replaces the parked run, so an overtaken answer
    that reached defer under a press displaced the newer fetch's parked landing, unpainted, and bailed itself at the
    release, leaving the old text under the old mtime with nothing re-asking (the Comments panel asks once per mtime);
    an answer that does not stand now reaches no hold. The same guard reads `wrap.isConnected` in place of the viewer
    id, which a replace-open moves to the new viewer, so a landing parked or in flight across a replace paints nothing
    into the replaced viewer's detached body and fires none of its hooks (file-view-landing-order-browser.test.ts,
    four scenes). file-view-copy-held-browser.test.ts pins the press over the real viewer and the release paths;
    file-view-copy-held.test.ts the helper alone. Round 2 refined the hold: it is taken for the primary button only (a
    right press yields no click, and Chromium's context menu takes its release, so a hold on one stood until the
    reader's next click with a landing parked under it), released on contextmenu as well, on the window in the capture
    phase, re-parked when a new press begins before the release's zero timer fires (unless a newer landing is parked
    under the new press, which then wins), and `defer` returns a promise that settles with the run, so a throw from a
    run the hold parked (an uncaught page error before, the old text standing under the new mtime with no error row)
    reaches the fetch's `.catch` and paints the failure row as an immediate landing's does
    (file-view-copy-held.test.ts, file-view-copy-held-browser.test.ts scenes 3 and 4,
    file-view-landing-throw-browser.test.ts). A keyboard press has the same window (a button's Space click is native
    to the keyup) and the hold reads pointer events only, so code-block.ts closes it from the button's side: Copy acts
    on the Space keydown, as Enter does, the key's default prevented, and the chat's Copy gets the same
    (file-view-copy-space-browser.test.ts, the pane and the chat modal). And the Copied acknowledgement goes to the
    button on screen of the fence with the pressed fence's SOURCE, carried across a swap inside its 1.2s window on the
    swap's own event (code-block.ts `acknowledge`: the text each Copy copies is recorded on its fence, the ancestors
    are read at the press, and a MutationObserver on their child lists follows a swap; of several fences with one
    source, the pressed one's ordinal among them; a write that rewrote or removed the fence acknowledges nothing,
    since the clipboard holds the old text and no fence on screen is the one copied): the held landing swapped the
    pressed button out a tick after its click and the label had gone to the detached node, so with the async Clipboard
    API the button on screen never changed and with the execCommand fallback it changed for a frame (round 3;
    file-view-copy-ack-browser.test.ts pins the real Clipboard API on a secure origin and the fallback on the pane and
    the chat modal, over writes that keep the fence). Round 3 read the fence's index among the fenced blocks under
    each ancestor, so a write that put a fence above the pressed one marked the new fence Copied and one that removed
    the pressed fence marked whichever fence took its index (the final fixes, 2026-09-09;
    file-view-copy-held-browser.test.ts scenes 5 to 7: the fence moved, removed, and one of two identical fences;
    scene 1 over a rewritten fence). And readPlace's top-block reads take an element showing under a pixel as not the
    top one (`edge + 1`, was 0.5): the browser snaps scrollTop to whole pixels, so a seat lands a block up to half a
    pixel from where it asked, and at the chat's end under the new leading a paragraph's last line seated 0.525px
    under the edge landed at 0.64 and was read back as the top block (file-view-place-blocks-browser.test.ts's bottom
    scene, whose scrollTop pin is exact again and names the top block by position as well as by text, since every
    blank Raw row reads as the same empty text). The prose leading, measured in round 1 and set in round 2: the slice
    declared none, so the note took the body's, 1.6 on the pane and the chat and 1.5 on the feed (a 101-line paragraph
    2416 against 2265px; the same note 6 percent taller on two surfaces than on the third), and the text named none;
    `.fileview-md` now declares `line-height: 1.5` (GitHub's) in both sheets, so the three surfaces set a line the
    same and a paragraph is the same height wherever the note is shown. file-view-prose-leading-browser.test.ts
    measures the ratio and the paragraph on the three surfaces at 100 and 115 percent, and pins the declaration in
    both sheets.

### Slice 4: one markdown configuration, Obsidian constructs included

A `md-config.ts` imported by render.ts, file-view.ts and anchor-map.ts registers gfm, the
double-tilde del rule, math (decision 1), front matter (a token spanning the block exactly, rendered
folded), footnotes, heading ids with GitHub slugs and in-body scrolling for `#` hrefs, callouts as
titled blocks, `==mark==`, wikilinks and embeds (decision 2), and `video`/`audio`/`source` in
`rewriteFigureSrcs`, which also applies decision 8 to remote figures: a src on an allowed host
(github.com and its image hosts, the kernel's own `/file` route, localhost) loads on open; any other
host shows a placeholder naming the host that loads the figure on one click; the list is a gear
setting, and a host the person allowed stays allowed for the session. A note's own attachments,
an Obsidian vault's included, are local files through the `/file` route and load on open.
Extensions, not string preprocessing: anchor-map lexes the same source.
Acceptance: each construct's fixture renders its element, `.katex` included in the files bundle; a
fixture with a figure on an unlisted host makes no request for it until the placeholder is clicked,
and a figure on github.com loads on open;
anchor-map maps a paragraph after front matter and after a footnote definition to its source offset;
a `#section` click scrolls `.fileview-body` and opens no tab. Tests: render and anchor-map fixtures;
a metafile check (math.ts in files.js).

Design note (2026-09-08): when math renders in every bundle, move the rendering to a Web Worker with a time budget, so
no formula can freeze the page. The macro bounds of Slice 1 (math.ts) are source-text heuristics, defence in depth
that new TeX shapes keep bypassing (a digit-named macro, an aliased definer and a definer stored in a body each got
past the reading before it); a worker bounds the time itself, whatever the shape, and the heuristics stay as the first
line.

**The Slice 4 build** (2026-09-09). Branch `mdviewer-s4`, on Slice 3's head (461c6f76, the fork's main merged in).
The gap analysis behind it ran every construct of a synthetic fixture through the real files, chat and feed bundles
in headless Chromium at 62cca6d0 and recorded what fetched on open; the browser legs below re-run those scenes over
the build. Where the code as built departs from the text above, why, and which test holds each rule:
1. *One module, on the singleton.* `ui/webview/md-config.ts` exports an idempotent `applyMdConfig()` that sets
   `gfm: true, breaks: false` and registers every extension in one list, `mdExtensions`: the double-tilde `del`
   rule (moved here from chat-md.ts and file-view.ts, which each held a copy), the math placeholders, front matter,
   footnotes, callouts, `==mark==`, wikilinks and embeds. render.ts, file-view.ts and anchor-map.ts each call it at
   load; chat-md.ts builds its `breaks: true` instance for the person's own words from the same list; the fill
   (`registerMdPostPass(renderMathPlaceholders)`) is registered beside the list. The singleton and not a private
   `Marked` instance, because `marked.use` writes the module defaults the static `Lexer.lex` reads: anchor-map.ts
   keeps `Lexer.lex` and sees every token the renderer rendered, whichever module loaded first (measured 2026-09-08:
   an instance's extensions never reach the static lexer). The eight test copies of the viewer's configuration
   (anchor-map.test.ts and its six siblings, file-comments-rendered-point-browser) call `applyMdConfig()`, and the
   four probe bundles (md-sanitize-postpass, -chat-links, -chat-schemeless, -chat-modified-click) arm the singleton
   the same way. The consequence, flagged to the person as an open ruling: the constructs render in chat replies
   too. A wikilink there is the dotted dead span showing the source as written (no directory), a reply opening with
   a `---` block that reads as YAML folds as front matter (item 3), `> [!NOTE]` in agent output becomes a titled
   block, `[^1]` with a definition and `==text==` render. The sheets dress the constructs in the chat's `.md` bodies
   too: each construct rule is doubled `.md X, .fileview-md X` in styles.css and feed.css (the chat's mark rule skips
   the comment highlight `mark.cmt-hl`; the bubble takes the white family it wears elsewhere), so a callout in a
   reply is a titled block and a `==mark==` the amber wash, not the browser's yellow-on-black (the review round 1;
   md-config-chat-styles-browser.test.ts reads both themes). md-config.test.ts executes the grammar and the
   idempotence and pins who calls it; render-math.test.ts pins the list's literal and the three callers;
   chat-md.test.ts pins the user instance; md-strikethrough.test.ts imports the rule from here.
2. *Decision 1, math everywhere.* file-view.ts's import of md-config.ts brings the grammar, the fill and KaTeX into
   files.js and feed.js (math-bundles.test.ts: a metafile of each bundle built with the shipped config holds
   math.ts, md-config.ts and katex; the viewer imports nothing from render.ts, code-block.test.ts). Production
   sizes, raw and gzip, before and after: files.js 495,838 / 148,117 to 866,609 / 240,946 (+370,771 / +92,829);
   feed.js 777,513 / 231,906 to 1,150,102 / 325,693 (+372,589 / +93,787); render.js 1,494,823 / 428,911 to
   1,511,207 / 433,636 (+16,384 / +4,725, the new extensions). KaTeX is 348,919 bytes of each viewer bundle.
   feed.css imports `katex/dist/katex.min.css` as styles.css does (esbuild inlines it and emits the fonts once, the
   same hashed names) and gains the `.katex-display` twin (parity head). md-sanitize-viewer-math-browser flips to
   the positive: the Files pane renders the same three KaTeX roots as the chat page; md-config-obsidian-browser's
   second test opens the feed page under feed.css built as the webview build builds it and reads KaTeX's face
   applied. Slice 5's math item is pulled forward, since math now reaches the viewer: anchor-map.ts skips a
   `.katex` root's text as a control and makes `mathInline` and `mathBlock` zero-text holes, so a paragraph with
   inline math maps around the formula and a display formula's paragraph is a hole block (before this, on the chat
   page, `walkInline`'s default case refused the whole paragraph). anchor-map-obsidian.test.ts and the browser leg
   select across the formula and get the TeX between. The fill's two fallback shapes, KaTeX's `span.katex-error` on
   TeX it cannot parse and the belt's `code.md-math-src` past a bound, are controls like `.katex` (anchor-map.ts
   FORMULA_CLASSES), so a display fallback keeps the 1:1 pairing and an inline one maps around; before that a display
   fallback took no element and every block after it paired one early, and the reader's place was a block off (the
   review round 1). A selection endpoint inside a formula's glyphs is the formula touched ("touches a formula", the
   Raw view offered at the formula's line); the edge that selects none of it maps the prose beside it; an endpoint
   inside another control (a back link's label, the fold label, a gate's label) stands at the control's edge, so a
   triple-click on a footnote definition maps its words (anchor-map-obsidian.test.ts tests 8 to 11,
   md-config-math-map-browser.test.ts). The block tokenizer's start hint names only a newline before a line the
   tokenizer will accept (math.ts nextBlockMath, one pass with a memo of the first closer per family): marked clips
   the paragraph at the hint and resumes it when the tokenizer says no, with a newline the source did not hold, so a
   rejected line (`$$x$$ is inline here.`, an unclosed `$$`) broke the raw tiling from that paragraph to the end of
   the note, and a match at the string's own start, one character into a line, cut `A $$x$$` in two
   (md-config-math-block-start.test.ts, with a linear-time bound: a note of 1,500 rejected candidates lexed in 13 s
   before, 155 ms after). KaTeX's flagged text takes a theme token, `--math-err` (math.ts MATH_ERROR_COLOR, which
   KaTeX writes into the span's inline style), declared in both theme blocks of both sheets at 4.5:1 or better on
   `--bg` and overridden to black in the print block, as the source fallback prints; KaTeX's default #cc0000 read at
   2.8:1 on the dark page (md-config-math-error-colour.test.ts, theme-parity.test.ts). The heading ids are minted
   BEFORE the fill, as sanitizeMd's caller pass (file-view.ts mintHeadingIds, md-sanitize.ts `own`): read after it,
   `# Ratio $\frac{a}{b}$` slugged KaTeX's glyphs in layout order (md-ratio-ba) where GitHub's slug and the note's
   own links spell md-ratio-fracab (md-config-fragment-landing-browser.test.ts). The Web Worker of the design note is
   NOT built: VS Code's webview CSP has no `worker-src`, and an asynchronous fill changes when `fireRendered` and
   the seat run over a paint (the comments panel and the reader's place would meet placeholders); the synchronous
   bounded fill of Slice 1 stays, and the note stays a direction.
3. *Front matter* renders as ONE element, `details.md-frontmatter` with a `summary` reading "Front matter" and the
   YAML in a `pre`, escaped text and never author HTML. The tokenizer fires only for the document's first token
   (`tokens === this.lexer.tokens && tokens.length === 0`: a quote's or a list item's body is lexed into a fresh
   array, so `> ---` inside a quote stays an hr; `state.top` is not that test), and only for a body that reads as a
   YAML mapping (isYamlMapping: every left-margin line a `key:` line, a `- ` item under a key, a `#` comment or
   blank) with no blank line after the opener (pandoc's rule), so a document that merely opens with a rule, a fence
   opening with `---` or prose between two rules keeps its blocks (the review round 1: a reply bounded by rules
   folded its first section into a closed block, and a `---` inside a fence closed the block early, so the fence's
   closer opened a block that swallowed the rest). Its raw tiles the source from offset 0, trailing blank lines
   included, so the block table's first span is `[0, 37]` where it was `[0, 3]` and `[4, 37]`, and the setext h2 the
   keys used to become (with its minted `md-title-...` id) is gone. anchor-map.ts treats it as a hole block ("the
   front matter") with the fold label a control; `tagOf` gives DETAILS. md-config.test.ts renders it (one element at
   the start, none mid-document or inside a quote; the rule-bounded, fenced and YAML shapes);
   anchor-map-obsidian.test.ts holds the block span from offset 0, the DETAILS tag, the hole's reason and the
   hr-without-YAML case.
4. *Footnotes*, our own extension (marked-footnote is not installed and renders at the end, which breaks the 1:1
   block pairing). `[^id]` renders `sup.md-fnref > a[href="#fn-id"][id="fnref-id"]` showing its number, and ONLY
   when the document defines the id (GitHub's rule; the lexer lexes every block before any inline text, so the
   definitions are known when a reference is lexed): `[^1]` with no `[^1]:` line stays as written, where it
   rendered a live-looking link to nowhere (the review round 1). A second reference to the same note gets
   `fnref-id-2`. A definition renders IN PLACE as `div.md-footnote[id="fn-id"]` with a back link
   `a.md-fnback[href="#fnref-id"]` first, one element per definition, so the paragraphs after it pair as before (the
   acceptance); its text runs as far as marked's paragraph rule reads a paragraph, so a lazy continuation line
   (GitHub's form) or a two-space indented one (Obsidian's) stays in the note and another definition, a list or a
   heading ends it (a four-space rule lost a wrapped definition's second line). A duplicate definition keeps its
   class and back link and drops its id, so `#fn-id` lands on the first. Numbering is by order of first reference,
   kept on the lexer instance (one per parse, the anchor map's static lex included), and a definition nothing
   refers to shows its id as a label with no back link. The ids reach the DOM prefixed `user-content-` and the
   `#fn-id` hrefs land through fragmentTarget in the viewer (md-config-obsidian-browser.test.ts clicks both ways
   over the Files bundle) and the chat's `#` delegate. A `[^n]: URL` line is a footnote now, where marked's `def`
   rule used to swallow it as a link reference (a note that used that form as a real link reference changes
   rendering). The shown number is a hole ("a footnote reference"); the back link is a control; the definition's
   text maps past its marker through the blockquote's suffix view. `tagOf` gives DIV. md-config.test.ts renders the
   reference, the in-place definition, the numbering, the URL-only definition, the undefined reference, the
   duplicate, the orphan and the continuation lines; anchor-map-obsidian.test.ts holds the DIV tag, the paragraph
   after a definition, the definition's own text and the number's refusal.
5. *Callouts.* A block extension tried before the built-in blockquote: GitHub's `[!NOTE]`, `[!TIP]`, `[!IMPORTANT]`,
   `[!WARNING]`, `[!CAUTION]` and Obsidian's `[!type] Title` with any type render `blockquote.md-callout` with a
   `p.md-callout-title` (the author's title, else the type capitalised) and the body lexed as blocks; `[!type]-`
   and `[!type]+` render a `details` closed or open with the title in its `summary`. Its extent is marked's own
   blockquote rule, borrowed, so a lazy continuation line with no `>` stays inside the tinted block as GitHub keeps
   it, and the start hint fires after a newline only (marked calls it on `src.slice(1)`, so a `^` alternative cut
   `a> [!note] b` into a one-letter paragraph and a callout; the review round 1). The type rides in a class
   (`md-callout-note`), not the `data-callout` attribute the design named, since the sanitizer drops every data
   attribute; the sheets tint by class through the page's own tokens (note and its kin the accent, tip green,
   important teal, warning amber, caution red, any other type the hairline). The title line is a hole ("a callout's
   title", since the marker is not shown and a missing title is generated); the body maps as blocks. `tagOf` gives
   BLOCKQUOTE, or DETAILS for a folded one. A `#` target inside a folded callout, a closed `details`, is revealed
   before the scroll (md-sanitize.ts revealFragmentTarget, the HTML spec's ancestor revealing steps, run by
   scrollToFragment for both viewers; before it the click scrolled to nothing with the fold shut). md-config.test.ts
   renders the five alerts, a titled type, the two folds, the lazy line and the mid-paragraph marker;
   anchor-map-obsidian.test.ts holds the tags, the body's blocks (a folded one's hidden body too) and the title's
   refusal, the generated title included; md-config-fragment-landing-browser.test.ts lands a heading link, a
   `[[#Heading]]` wikilink and a footnote reference inside a shut fold.
6. *`==mark==`* renders `<mark>` and maps by delimiter width like em and strong; the opener must touch its content,
   so `a == b` in prose stays literal, and may not touch a word or another `=` on its outside (the run of `=` is
   exactly two; an ASCII letter or digit before it refuses, so CJK prose with no space before a highlight is not
   refused), so `a==b and c==d` and `a===b` in a sentence or a heading stay literal where the plain delimiter rule
   paired two comparisons into one highlight (the review round 1). md-config.test.ts renders it and keeps the
   comparisons literal; anchor-map-obsidian.test.ts maps its text by the delimiters.
7. *Decision 2, wikilinks and embeds.* The renderer emits an anchor ONLY when the per-parse walkTokens of the file
   kind (file-view-links.ts viewerWalkTokens, run by mdBlock for the file kind alone) stamped the token `resolved`:
   `[[Note]]` becomes `<a href="Note.md">Note</a>` (`.md` appended unless the target names a file type Obsidian
   opens, KNOWN_EXT_RE: `[[img.png]]` and `[[paper.pdf]]` keep their extension, and a dotted title such as
   `[[Note.v2]]`, `[[Release v1.0]]` or `[[Node.js]]` is a note, where any dotted target read as a file with an
   extension and linked a file that does not exist; the review round 1), `[[Note|alias]]` shows the alias,
   `[[Note#Heading]]` carries the fragment, `[[#Heading]]` is a section link of the same note; #347's link pass then
   turns each into a path link to `<dir>/Note.md` with the fragment in `data-frag`, no existence check. Everywhere
   else (a chat reply, a URL document) the same text is `span.fv-wikilink.fv-dead` showing the source as written,
   brackets included (`[[Note]]`, `![[img.png]]`, an R-style `matrix[[0]]` too), with a title that says why and
   names no surface (the review round 1: the span showed the alias or target alone, so a reply's reader could not
   tell a wikilink from plain text, and its title spoke of "the viewer" to a reader of a reply). `![[image.png]]`
   renders an `<img>` when resolved, so rewriteFigureSrcs loads it from the file's folder and `![[image.png|300]]`
   sets its width; `![[Note]]` is a link-shaped chip `a.fv-embed`; unresolved, an embed is the dead span too (an
   `<img src="image.png">` in a reply would fetch from the page's own origin). An anchor's shown text is the source
   text at `textOffset` in the raw, so the anchor map places it exactly (a dead span is never mapped: a reply is
   not, and the URL kind keeps its place by blocks). The comments panel's embed grammar and the host's
   (`imageEmbeds` in file-comments.ts and tools/file-comments-host.mjs) read the `![[...]]` form: it was a one-regex
   addition, so the limit the design allowed for was not taken; file-comments-panel.test.ts and the host's tests
   hold both readers.
8. *rewriteFigureSrcs* reads every attribute a figure fetches through (figure-gate.ts figureRefs): an img's `src`
   and `srcset`, a `source`'s `src` and `srcset`, a video's `src` and `poster`, an audio's and a track's `src`, an
   svg `image`'s or `feImage`'s `href` and `xlink:href`. A srcset is rewritten candidate by candidate with its
   descriptors kept (HTML's own parse, a comma inside a URL kept). Only an img's `src` keeps `data-fv-src`, the
   one attribute the panel pairs an embed by. An `xlink:href` is folded into `href`: when both stand, `href` wins
   (SVG 2's rule) and the xlink attribute goes either way, so the element carries one attribute every reader agrees
   on. file-view-figures-absolute.test.ts's selector pin is the gate's `FIGURE_SEL` now, with a case per shape. An
   `feImage` never reaches the rewrite or the gate today: the sanitizer's `svg` profile (md-sanitize.ts MD_PURIFY, no
   `svgFilters`) drops a filter's primitives first, so that arm is a guard for a wider profile, pinned over the
   stand-in together with the profile itself (a wider profile must bring a browser leg; the review round 1).
9. *Decision 8, the gate* (figure-gate.ts, run by mdBlock after rewriteFigureSrcs on the sanitized DOM). The allowed
   set is the gear's `figureHosts` (settings.ts `FIGURE_HOSTS_DEFAULT`: github.com, raw.githubusercontent.com,
   user-images.githubusercontent.com, camo.githubusercontent.com, avatars.githubusercontent.com,
   objects.githubusercontent.com, private-user-images.githubusercontent.com, github.githubassets.com, localhost,
   127.0.0.1; exact names, no wildcard) plus the page's own origin and the kernel's (`window.__rompKernelBase`),
   which every local figure goes through, plus the hosts clicked in this page (`loadedHosts`, a module Set that
   lives as long as the page, which is how Decision 8's "for the session" is built: the chat webview, the feed, the
   Files pane and each browser tab each remember their own, so a host clicked while reading one file is loaded for
   every file opened in that page afterwards, until the page reloads; the viewer's Reload or a Raw and back keeps a
   clicked host loaded, an emptied list gates a host the setting allowed; figure-gate.test.ts holds the set, and the
   gate leg re-opens the file and reads both clicked hosts loaded on open). An entry of the list is read down to its
   host name through the URL parser (settings.ts figureHostName, the reading remoteHost gives a source: an address
   pasted whole, a port or a path is stored as the host alone, an internationalised name in its `xn--` form, an
   IPv4 address without leading zeros; an entry with its own scheme is parsed as it stands, any other under
   `http://`), once per host; a line the parser refuses is kept as typed, allows nothing, and is named under the
   list in the gear (gear.js figureHostsNote). Before that a stored `https://cdn.test` or `cdn.test:8080` was a dead
   entry that gated the host it named, with no sign in the gear (the review round 1). A media
   root (img, video, audio, picture, svg; a `source` or `track` through its parent) with a source on another host
   is wrapped in `span.fv-gate[data-act="fv-load"][role=button][tabindex=0][data-fv-host]`, its label "Image from
   host. Click to load." (or Video, Audio), sized by the author's pixel `width` and `height` or the sheet's minimum
   box; every fetching attribute moves to `data-fv-gated-<name>` and `data-fv-src` to `data-fv-gated-fv-src`, so
   nothing leaves the page and no embed pairs while gated. The element stays inside the placeholder, which keeps the
   region layer's contract: with the panel open the layer wraps THE img inside the placeholder, and the click
   leaves the wrapper standing around the loaded picture (the leg reads both). The click is delegated on
   `.fileview-body` (and the URL viewer's body), never bound to the placeholder, since every paint rebuilds the
   DOM; Enter and Space on a focused placeholder do the same in both viewers (file-view.ts gateKeys: the URL
   viewer's `delegate` reads clicks alone, so its placeholder ignored the keys until the review round 1;
   md-config-url-gate-keys-browser.test.ts); the restore is the acknowledgement. One click restores every
   placeholder waiting on that host alone and relabels one waiting on more. The gear's list reaches an open
   document through the settings listener (regateFigures on `storage` and `romp:settings`). Nothing in the gate
   FINDS an element by class, since the sanitizer keeps an author's `class`: the placeholder by its `data-act`, its
   label by `data-fv-label` (LABEL_MARK, which the sheets' hide rule keys on too), so an author's
   `<text class="fv-gate-label">` inside a gated svg no longer takes the label's text and a `<span class="fv-gate">`
   around prose survives a click or a settings event with its text (the review round 1;
   md-config-figure-gate-authored-browser.test.ts). The srcset parse breaks on HTML's ASCII whitespace alone (a JS
   `\s` stopped at a no-break space, so `github.com<nbsp>@evil.test/x.png` read as github.com to the gate while
   the browser fetched evil.test) and leaves parentheses at the first `)` as HTML's descriptor tokenizer does, and
   every srcset under a judged root is written back in the gate's own spelling before the judgment, so the
   attribute the browser reads is the one the gate parsed. The placeholder's text is skipped by the anchor map
   (isControl) and by the reader's place (reader-place.ts noteText), so an html block holding a gated figure at the
   top of the view keeps the place across a paint (its label had read against a parse of the block's source that
   reads nothing, and the Raw switch seated nothing; md-config-figure-gate-place.test.ts and its browser leg). The
   URL kind names the document's own host beside the list: the URL viewer fetches with `mode: "same-origin"`, so
   that HOSTNAME is the page's, but the gate compares origins (remoteHost), so a figure on the document's hostname
   under another scheme or port loads on open only through this arm (the gate leg's URL scene holds it: fx-alt,
   fx-port). The chat's `md()` is not gated (recorded). Measured on open, DPR 1, the fixture of
   file-view-figures-gate-browser: the one request that left the page was github.com's picture; `/file` served the
   file and its `![](fig.png)`; six placeholders held remote.test's img, srcset, poster, picture, svg and second
   img and one held other.test's. After the click on one remote.test placeholder: remote.test's img.png, img2.png,
   poster.png and svg.png were fetched and `/file` served local.png; the 2x srcset candidate was not picked at DPR
   1; for the `<picture>`, Chromium took the fallback img rather than the source's srcset when both came back on an
   element already in the document (the leg accepts either). A `<picture>` is gated whole, so its local fallback
   waits with the remote source. The gear's row is a textarea, one host per line; gear.js holds a copy of the
   default list, the host reading and the normaliser (it cannot import settings.ts), and gear-figure-hosts.test.ts
   holds them equal to settings.ts's. figure-gate.test.ts covers the pure parts (the srcset parse, remoteHost, the
   allowed set, the normaliser); settings.test.ts and md-config-figure-hosts.test.ts the field and its reading;
   docs/reference.md and the guide's Figures paragraph describe it.
10. *Not built here.* Obsidian's `%%comment%%` and `#tag` (the text names them for awareness only) stay literal.
   Slice 5's other items (refusal reasons for the remaining token names, goTo into a closed details) are untouched.

### Slice 5: comments anchor on real notes

Pair blocks inside an unclosed HTML container (a flattened walk); match code quotes raw; math tokens
as holes, no token names in refusals; report the first obstacle in document order; open `<details>`
ancestors in goTo; overlapping `.fc-hl` keep one wash and a click opens every card under it; paintAll
hints with the last located start; strip cell delimiters from a table quote; offer Comment on
`selectionchange`. Acceptance: selections after the wrapper and details containers map; the `total =
a * b * 2` comment paints in Rendered; the math paragraph maps around the formula; a Raw comment
across two cells paints; a keyboard selection offers Comment. Tests: anchor-map and file-comments
fixtures. One more for the flattened walk, found in Slice 1's merge review (2026-09-08) and identical on main:
the resync across an html block (`runFits`, anchor-map.ts) accepts the first end from which the next block lines
up by whitespace-stripped text alone, so when a node the block rendered carries exactly the next paragraph's text
(a kept `<div>Go</div>`, or a `Go` hoisted out of a dropped `<form>`) the block takes no node, its own rendered
text maps to that paragraph's source offsets, and the blocks after it pair one node early: a later paragraph whose
text recurs maps to the wrong occurrence's offsets, the rest refuse. A tag test on a mapped block (`tagOf` already
names its element) closes the kept-element and hoisted-text shapes; an html `<p>` carrying the next paragraph's
text needs the run confirmed past it. Acceptance: the text-alike html node is refused and each paragraph after it
maps to its own offsets.

### Slice 6: reaching a section without scrolling

`.fileview-body` takes `tabindex=0` and focus after paint unless the composer holds it; an Outline
action lists headings by level; per-path scroll memory, persisted with the Recent entry;
`openFileView(path, sid, { at })` (line, offset or heading) through the viewFile relay, sharing the
in-file link route's `:line` grammar (fork PR #347); a HEAD on focus and visibilitychange, showing
"Changed on disk: Reload" when the mtime moved. Acceptance: PageDown moves scrollTop with no prior
click; choosing the 40th heading in Outline puts it at the top; a note reopened from Recent returns
to its scrollTop; a todo link with a heading target opens at that heading; a moved mtime on focus
shows the note bar.

### Slice 7: every failure says what happened

The render catch shows Raw rows under a `.fileview-err` line; a failed figure shows an inline error
naming its src; every failure path fires the paint hooks and the seam exposes `error()`; the host
strips the BOM and the kernel re-prepends it on save; a Latin-1 file's note bar says why Edit is off;
an empty file says so; Raw splits rows on CR, CRLF and LF. Acceptance: every case shows text, never
a blank or bare glyph; `mode()` answers raw after a thrown render; a failed reload ends the panel's
wait at once; change marks paint on a BOM file whose saved bytes still begin EF BB BF; a three-line
CR-only file gives three Raw rows. Tests: file-view, seam, host;
`tests/test_kernel_file_comments_save.py`.

### Slice 8: a cell and a code line are commentable from Rendered (ruling 2026-09-07, decision 7)

Exact mapping for tables and fenced code: the anchor map learns how marked lays out a table cell and a
code line, so a selection made in the Rendered view inside either maps to the note's source offsets
and the highlight lands on the right occurrence; the Raw fallback stays for shapes the map still
refuses. Large; built directly after Slice 5, with Slice 5's test files extended. Acceptance: a
comment on a cell and on a code line made from Rendered paints in both views after a reload; a
selection spanning two cells is refused with the reason named.

## Decisions

1. **Math everywhere or nowhere.** KaTeX adds about 270KB of script and 25KB of CSS to the files
   and feed bundles; nowhere drops it from the chat. Ruling (2026-09-07): everywhere; KaTeX ships
   in the files and feed bundles too, so a note's math renders wherever the note is shown.
2. **Wikilink resolution.** No vault root is known: `<dir>/Note.md`, an upward `.obsidian/`
   search, or an unclickable styled span. Ruling (2026-09-07): `[[Note]]` resolves to
   `<dir>/Note.md` beside the note and clicks through the in-file link route (fork PR #347); a
   wikilink that does not resolve renders as an unclickable styled span.
3. **Light-theme face.** The 2026-08-31 monospace ruling applied to viewed notes, or a sans
   `--font-doc` token in both themes. Ruling (2026-09-07): a `--font-doc` token, sans in both
   themes; the 2026-08-31 monospace ruling was about chat output, not viewed notes.
4. **Reading measure.** A centred column near 80ch at about 15px, or the left-pinned column the
   text-size change (fork PR #348) makes fluid. Ruling (2026-09-07): a centred column near 80ch
   at about 15px, scaled by #348's text-size control.
5. **Grammars.** Ten are registered; rust, go, c, java, sql and toml cost 3 to 12KB each. Ruling
   (2026-09-07): add those six; others on request.
6. **Inline `style`.** Strip it as GitHub does (existing coloured spans go plain), or keep
   colour-only declarations through a DOMPurify hook. Ruling (2026-09-07): keep colour and
   background-colour declarations through the hook and strip every other property, so coloured
   spans in existing notes survive and layout or positioning styles cannot reach the page.
7. **Exact mapping for tables and code** (large), so cells and code lines map from Rendered, or
   the designed refusals with Raw fallback. Exact mapping means teaching the anchor map how
   marked lays out a table cell or a code line, so a selection made in the Rendered view inside
   one maps back to the note's source offsets; today such a selection is refused and the person
   comments from the Raw view. It is a slice of its own by size, not a lesser priority. Ruling
   (2026-09-07): build it as Slice 8, directly after Slice 5, with the same acceptance shape (a
   cell and a code line commentable from Rendered, the highlight landing on the right
   occurrence).
8. **Remote images.** Load on open (a tracking pixel fires), gate behind a click naming the host,
   or proxy through the kernel. Ruling (2026-09-07): an allowlist of hosts loads on open
   (github.com and its image hosts, the kernel's own /file route, localhost), and every other
   host is gated behind one click that names it; the list is editable in the gear and the gate
   remembers a host the person allowed for the session.

## Out of scope

Text size, fluid width, table reflow, whole-word cells (fork PR #348); path and http links in files,
the `:line` suffix (fork PR #347); the PDF viewer; emoji shortcodes; another parser; editing the rendered
view in place; the two audit items its refuters overturned.
