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
pane (`anchor-map.ts:514`); code-line comments containing `*`, `_` or `#` never paint
(`anchor-map.ts:1034`); table cells and code refuse Rendered selection (`anchor-map.ts:873`); a
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
