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
     block skip 0). Since the Slice 5 build (its note, items 1 and 1b) the map pairs the wrapper to itself and each
     block nested in it to its own element, and the reader's place descends into the wrapper, so refusals (1) and (2)
     are history: the html, wrapper-end and edits legs pin exact round trips from a nested paragraph, a picture or a
     rule after a wrapper and the README pair, and a Raw row of the wrapper's own still seats nothing.
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
merged in (8362983a), and again at fb42df7d once Slice 2 had landed as fork PR #396. The gap analysis behind it ran
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
   runs for the reflow (the ResizeObserver's report is the layout's own event; one write per report; since 2026-09-09 the
   property is registered non-inherited and written on each top-level table instead, since a write on the body restyled
   every node under it per width change: file-view-body-width-browser.test.ts), and `max-width:
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

**The Slice 4 build** (2026-09-09). Branch `mdviewer-s4`, on Slice 3's head (fb42df7d, the fork's main merged in),
with the fork's main merged in again at 0b5e23be once Slice 3 had landed as fork PR #407. The gap analysis behind it
ran every construct of a synthetic fixture through the real files, chat and feed bundles in headless Chromium at
03b95284 and recorded what fetched on open; the browser legs below re-run those scenes over the build. Where the code
as built departs from the text above, why, and which test holds each rule:
1. *One module, on the singleton.* `ui/webview/md-config.ts` exports an idempotent `applyMdConfig()` that sets `gfm:
   true, breaks: false` and registers every extension in one list, `mdExtensions`: the double-tilde `del` rule (moved
   here from chat-md.ts and file-view.ts, which each held a copy), the math placeholders, front matter, footnotes,
   callouts, `==mark==`, wikilinks and embeds. render.ts, file-view.ts and anchor-map.ts each call it at load;
   chat-md.ts builds its `breaks: true` instance for the person's own words from the same list; the fill
   (`registerMdPostPass(renderMathPlaceholders)`) is registered beside the list. The singleton and not a private
   `Marked` instance, because `marked.use` writes the module defaults the static `Lexer.lex` reads: anchor-map.ts
   keeps `Lexer.lex` and sees every token the renderer rendered, whichever module loaded first (measured 2026-09-08:
   an instance's extensions never reach the static lexer). The eight test copies of the viewer's configuration
   (anchor-map.test.ts and its six siblings, file-comments-rendered-point-browser) call `applyMdConfig()`, and the
   five probe bundles (md-sanitize-postpass, -chat-links, -chat-schemeless, -chat-modified-click and -anchor-map) arm
   the singleton the same way (the first four had registered the chat's extensions beside the viewer's options,
   -anchor-map the viewer's options alone; this count read four until the review round 7). The consequence, flagged
   to the person as an open ruling: the constructs render in chat replies too.
   A wikilink there is the dotted dead span showing the source as written (no directory), a reply opening with a `---`
   block that reads as YAML folds as front matter (item 3), `> [!NOTE]` in agent output becomes a titled block, `[^1]`
   with a definition and `==text==` render (two more shapes of the same ruling, from the review round 2: a section of
   a reply between two rules whose body is `#` lines alone reads as a comment-only YAML mapping and folds, as pandoc,
   Jekyll and Obsidian read it; bash's `[[ -f x ]]`, Python's `[[1]]` and R's `lst[[1]]` are the dead span, text
   preserved). The sheets dress the constructs in the chat's `.md` bodies too: each construct rule is doubled `.md X,
   .fileview-md X` in styles.css and feed.css (the mark rule keys on the class the renderer emits, `mark.md-mark`, so
   neither the chat's comment highlight `mark.cmt-hl` nor the panel's marks are its subject, the review round 3; the
   bubble takes the white family it wears elsewhere), so a callout in a reply is a titled block and a `==mark==` the
   amber wash, not the browser's yellow-on-black (the review round 1; md-config-chat-styles-browser.test.ts reads both
   themes). Round 4 of the review re-inked two constructs in the bubble and named every construct in the print block:
   in the bubble a footnote definition and the front-matter fold took the page's dim grey from their shared rules,
   1.66:1 (dark) and 1.39:1 (light) on the saturated fill, and read now in the bubble's own ink, with the quote's 0.40
   white for the footnote's rail and the fold's box; and a callout's rail and ink are set outright there for both of
   its forms, since the bubble's blockquote rule outranked the shared callout rule for the blockquote form alone and
   `> [!note]` and `> [!note]-` one line apart wore different rails and inks (the same leg types both). Round 5 held
   every ink the slice sets in the bubble to 4.5:1 on both fills, measured over the wash it sits on, and the bubble's
   washes darken the fill (a white wash under white ink lowers the ratio): the mark's wash is an 18% black (6.40:1
   dark, 6.92:1 light; the code span's 20% white wash it copied put the ink at 3.35:1 and 3.51:1), a callout's ink is
   the bubble's own (inherit) over an 8% black wash, both forms alike (5.36:1 dark, 5.85:1 light; round 4's 0.88 tint
   over the 7% white wash `--callout` gave them read 3.59:1 and 3.87:1) and, since round 6, both forms in the bubble's
   own face (the bubble's quote rule sets the blockquote form in `--font-prose`, the light theme's mono for the
   assistant's quoted words, and reached the blockquote form alone, so on light `> [!note]` read in ui-monospace and
   `> [!note]-` one line below in the sans; a callout is the person's own construct, and the quoted passage keeps its
   mono; the chat-styles leg reads one computed font-family for both forms, their titles and their bodies, on both
   themes), a dead wikilink keeps the shared rule's dotted underline at the bubble's full ink (the shared 0.7 opacity,
   tuned to `--fg` on `--bg`, put white on the fill at 3.10:1 and 3.38:1), and the fold's YAML takes the page's `--fg`
   in the bubble's page-coloured pre well (13.96:1 light, 10.38:1 dark; round 4's inherit was the bubble's white on
   the light theme's cream, 1.19:1, where the `var(--dim)` it inherited before read at 5.99:1; the chat-styles leg
   opens the fold and reads the pre). In print the footnote definition, the front matter and a gated figure's
   placeholder print black ink and black borders with the placeholder's wash off, and a callout's `--callout` is
   black, the variable its rail and wash ride, so every callout prints a black rail over a faint neutral wash beside
   the plain quote's (the construct rules, two classes deep, outranked the print block's one-class ink rule and its
   border list; md-config-print-constructs-browser.test.ts measures the pane, the chat modal and the feed page under
   print media and back). Round 5 named the embed chip on the construct line too, `a.fv-embed`, whose hairline box
   printed white on white on the feed page, gave the `==mark==` one print wash, 15% black, where it kept 35% of the
   theme's amber and the same note printed two tints from two themes (both in
   md-config-print-constructs-browser.test.ts), and opened a display formula's scroll box in print as the table's is:
   a formula of the page's own takes the table's room and shift, so one between the column and the body prints whole
   and centred across both gutters (an 836px formula in a 762px column, cut at the column's edge before), a narrow one
   keeps its column box and an equation tag its place at the column's edge, and one wider than the paper starts at the
   gutter and is cut at the paper's edge, KaTeX's nowrap being what no sheet rule scales
   (md-config-print-wide-formula-browser.test.ts measures the three shapes on the pane and the feed page); a display
   formula inside a callout, a quote or a list item takes the open box and not the room and shift, as a nested table
   takes neither, so one wider than its container runs from the container's left edge past its right edge to the
   paper's edge, start-aligned, which shows more of it than the screen's clip did (round 6, recorded: the shift would
   put ink across the container's rail or a list's bullet, and the sheet cannot read a container's inset). Round 6
   also prints the source fallback's dotted underline black beside its ink (`code.md-math-src`: the shared rule names
   the underline's colour outright, `text-decoration-color: var(--dim)`, so the block's `color: black` did not carry
   to it and the cue printed at 2.56:1 on white from the dark themes and in another grey from the light one;
   md-config-print-constructs-browser.test.ts reads it on every cell). md-config.test.ts executes the grammar and the
   idempotence and pins who calls it; render-math.test.ts pins the list's literal and the three callers;
   chat-md.test.ts pins the user instance; md-strikethrough.test.ts imports the rule from here.
2. *Decision 1, math everywhere.* file-view.ts's import of md-config.ts brings the grammar, the fill and KaTeX into
   files.js and feed.js (math-bundles.test.ts: a metafile of each bundle built with the shipped config holds
   math.ts, md-config.ts and katex; the viewer imports nothing from render.ts, code-block.test.ts). Production
   sizes, raw and gzip, before and after: files.js 495,838 / 148,117 to 866,609 / 240,946 (+370,771 / +92,829);
   feed.js 777,513 / 231,906 to 1,150,102 / 325,693 (+372,589 / +93,787); render.js 1,494,823 / 428,911 to 1,511,207
   / 433,636 (+16,384 / +4,725, the new extensions). KaTeX is 348,919 bytes of each viewer bundle. Its DOM is
   decision 1's other cost, measured in the review round 7 on the freeze bench's medium note (3,000 lines, 162
   inline and 52 display formulas): 214 `.katex` roots hold about 8,000 more elements, the mount is 160 to 200 ms
   slower to first paint, the panel's cards placement and a comment add 20 to 25% slower, and the one reflow at a
   divider release or a resize reads one vsync longer; the drag itself moves a ghost line and lays the pane out once
   at release, and math-free every number is within noise of main. feed.css imports `katex/dist/katex.min.css` as
   styles.css does (esbuild inlines it and emits the fonts once, the same hashed names) and gains the
   `.katex-display` twin (parity head). md-sanitize-viewer-math-browser flips to the positive: the Files pane
   renders the same three KaTeX roots as the chat page; md-config-obsidian-browser's second test opens the feed page
   under feed.css built as the webview build builds it and reads KaTeX's face applied. Slice 5's math item is pulled
   forward, since math now reaches the viewer: anchor-map.ts skips a `.katex` root's text as a control and makes
   `mathInline` and `mathBlock` zero-text holes, so a paragraph with inline math maps around the formula and a
   display formula's paragraph is a hole block (before this, on the chat page, `walkInline`'s default case refused
   the whole paragraph). The highlight paints the formula with its passage: paintRendered wraps a run of adjacent
   siblings (text and inline formulas) in one mark, and a formula whose TeX the range holds is included even at the
   range's edge or alone, so a comment on `Inline $x^2$ math and` is one box and not two with the formula bare
   between them; a display formula, a block of its own, is never wrapped (the review round 2;
   anchor-map-obsidian.test.ts, md-config-math-map-browser.test.ts). A mark reads the top-level blocks it touches
   and no other, the covered formulas' among them: on the text path since the fork's Files pane freeze fixes met the
   slice (their scoped walk kept, the formulas' blocks added to it) and, since the review round 7, on the
   formula-only path too (paintRendered's `unitsUnder`, shared with wrapBetween; 40 formula-only marks over a
   26k-node document read 142 ms a pass against 6.4 ms scoped). A run of whitespace-only text nodes between blocks,
   the pair the sanitizer leaves where a block-level comment or a `<style>` stood, is never a mark of its own (round
   7: wrapRuns skipped one such node alone and ringed the pair as an empty box between the blocks, which moved
   everything below down 30 px on every fresh Rendered paint; anchor-map.test.ts and anchor-map-obsidian.test.ts
   hold both). Since round 12 the painter predicts two things about white space, each exact, and paints every other
   whitespace-only text node of a range for the browser's layout to judge (the layout-time trim, below). One: a text
   node directly under the render root is skipped when it is `\s` and format characters alone (anchor-map.ts
   ROOT_BLANK). The top-level children are what the block pairing reads, so such a node is never the passage's text,
   and a mark there would be a top-level child of the root that the next pairing meets (anchor-map.test.ts,
   anchor-map-obsidian.test.ts and md-config-paint-collapsed-blank.test.ts hold that no mark is a top-level node);
   round 11's guard read `\s` alone and painted a lone U+200B between two top-level html paragraphs, pasted from a
   web page, as a box on a line of its own. Two: a text node of collapsible white space (HTML's ASCII five, space,
   tab, line feed, form feed and carriage return; never JavaScript's `\s`, so a node of no-break or ideographic
   spaces between two blocks is a blank line the note renders, painted as on main) whose nearest non-blank sibling
   on both sides is a block-level box, or whose parent is one and has no such sibling on that side, and that stands
   under no `pre`, is skipped without a measurement: the block-neighbour pre-skip (CSS 2 section 9.2.2.1, an
   anonymous inline box holding only collapsible white space between block-level boxes is not rendered, and a
   block's leading and trailing white space is collapsed away; under an author's `pre` nothing is collapsible, so
   two spaces or a tab between two block children render a line of their own, 16.86 and 67.44 px at 14px sans-serif,
   and the node is painted and measured like every other blank, a newline alone measuring zero and unwrapped: round
   12's pre-skip skipped the rendered spaces, a ring gap inside the pre, and round 13 exempts a `pre` ancestor;
   md-config-paint-trim-fixpoint.test.ts and its browser leg). BLOCK_BOXES is derived, every tag the sanitizer keeps
   that Chromium lays out as a block or a table's part, plus `.katex-display`
   (md-config-paint-whitespace-browser.test.ts holds it against DOMPurify's allowlist and the computed display,
   md-config-block-boxes.test.ts in node against the HTML Standard's Rendering section's block-level tags,
   anchor-map-fixtures/block-tags.json), and the reading saves the mark, the measurement and the unwrap for the
   hundreds of "\n" nodes marked leaves between a list's items, a quote's paragraphs or a fold's blocks; outside a
   pre the trim alone gives the same answer on every scene, so the reading is an optimisation kept because it is
   exact where it applies. The trim (anchor-map.ts trimCollapsedMarks, exported): after the paint, every mark whose
   text is blank (no letter, digit, punctuation or symbol in it, or the hangul fillers alone; the alphabet picks
   what is MEASURED and never what is unwrapped, so a candidate that renders, U+093F alone as a dotted circle, keeps
   its mark) is measured with a Range over each of its text nodes, their client rects' widths summed (never one
   Range over the mark's contents: two comments over one passage nest their marks, and a Range over the outer mark's
   contents reads the inner mark's border box, 4 px of padding a level, so round 12 peeled such a nest one level per
   pass; round 13), and unwrapped at zero width when the mark has a box of its own (one under a display:none
   ancestor is kept, and the panel measures it again on the show, by the seam's reflow report when a frame ran while
   the pane was hidden or in the frame the hidden trim armed when none did, the hide and the show in one task; the
   Event-based sentence below): a collapsible space at a line's edge or at the point where the line wraps, one after a
   neighbour ending in a space or beside an element that renders nothing (an empty anchor, an audio element without
   controls, a floated image, a picture without an image), a zero-width, bidi or soft-hyphen character alone, a
   newline the browser drops; a rendered blank keeps its mark (a no-break or ideographic space, a space between two
   inline children on one line, the space beside an svg icon, an image or a checkbox). Three shapes, each measured on
   the round 12 prototype: two-phase (every candidate measured, then every collapsed one unwrapped, one layout per
   pass; a measurement per unwrap cost 12 s on a paragraph of 5,000 code spans against 0.4 s), batched (paintRendered
   trims its own marks by default, `PaintOptions.trim`; the Comments panel paints every comment of a pass with `trim:
   false` and runs the trim once over the pass's marks, file-comments.ts paintAll and trimBlanks, one layout for the
   pass, and a card whose every mark was a collapsed blank is re-filed as not painted, as the unbatched paint returns
   null) and to a fixpoint (a mark's own 2 px side padding is in the layout, so an unwrap can move a wrap point and
   collapse a later blank; until a pass unwraps nothing or no candidate is left, a loop that ends by construction
   since each continuing pass removes a mark, with TRIM_PASSES_MAX = 20 as a safety cap and a call that reaches it
   with candidates standing counted in TRIM_STATS.capped; over round 12's 91 scenes 42 paints took one pass, 34 two
   and one three, and the paragraph of 5,000 links takes eight passes fresh at 700 px and twelve after a narrowing
   from 800 to 400 px, where round 12's cap of three left 366 and 266 padding-only marks standing; round 13,
   md-config-paint-trim-fixpoint.test.ts and its browser leg). Event-based: the panel re-trims its standing marks
   when the seam reports a reflow (Slice 2's onRendered with `why` "reflow", a width change or a text-size step) in
   the frame the cards are re-placed, and since round 13 on two layout changes the seam never reports, the body's
   captured `load` (a figure's bytes landing, a gated figure's restored media among them) and the document's
   FontFaceSet `loadingdone` (a face arriving under the sheet's font-display: swap), which re-wrap the lines with no
   width report, each folded into the panel's layout frame (one trim per frame however many events ask, the cards
   placed over the marks that stay); and when a trim finds the pane without a box (a display:none iframe, the phone
   shell's tab switch, where every blank mark measures nothing and is kept) it asks for a frame and measures the
   marks again there, once per event and never per frame: when the hide and the show fall in one task that frame is
   the first after the show and re-trims it, and when a frame runs while the pane is hidden (Chromium runs a
   display:none frame's requestAnimationFrame at full rate, so every hide that outlasts a frame; round 14) the armed
   frame runs hidden and keeps every mark, and the seam's width observer reports the hide and the show as reflows,
   the show's report re-trimming (md-config-paint-retrim-events-browser.test.ts, five legs over the real panel; leg
   4 the one-task shape, leg 5 the hide across frames, with two trims per event while hidden and never one per frame);
   and when the pending target alone is painted or unpainted (a composer opened, closed or moved: file-comments.ts
   repaintPresel), whose 2 px side padding moves the wrap points of the lines it shares with a highlight: round 14
   trimmed the standing marks at once in the same call (the item of fourteen links selected whole over its comment had
   left two, three, four and four padding-only highlight marks at 600, 500, 400 and 300 px for as long as the composer
   was pending), and since round 15 the repaint is a paint pass over the line boxes the target enters and leaves
   (lineBoxOf: the box is the block whose width does not follow its content, past the embed chip's inline-block and a
   table's parts, round 16; the boxes are closed under the highlights standing in them, every box a repainted
   highlight's own marks stand in read too until no highlight is new; those highlights are unpainted and painted again
   in cards() order, the pass's, and the change marks whole-document through paintChanges when one stands in any of
   the boxes, since paintChanges has no per-change scope and a per-box unpaint would split a change spanning boxes, at
   a price on a note of a hundred paragraphs with an insertion in each of 12 to 14.5 ms an open and 11 to 12 ms a
   Cancel against 1.7 to 3.6 and 1.1 to 1.6 ms with no change mark in the target's paragraph; the target inside them,
   then the one trim; round 15 read the target's boxes alone and painted the highlights in the order of their first
   marks, so two overlapping comments whose order by time was not their order in the text swapped nesting at every
   open and close and back at the next pass, the click on the overlap opening the other card meanwhile, a highlight
   painted again in a box the target never touched landed inside the marks standing there, and a target on the chip's
   text moved the paragraph's wrap points while no highlight of it was repainted), since a trim alone left the
   highlight's blanks trimmed at the old wrap points bare where they rendered at the new ones, 4 and 2 of the item's
   spaces at 300 and 400 px selected whole, 2 and 1 with four links selected, and 39 of the 120-link item's 119 at 800
   px while the composer stood, and 4, 4, 3 and 2 after Cancel at 300 to 600 px until the next paint pass; a repaint
   that adds and removes no Rendered mark (a reply, a comment on a deletion or a detached change, which
   startChangeComment opens by id alone since fork PR #657 renamed the change card's Reply to Comment on this change,
   a re-place, a comment on the file, a region, a refusal, the Raw view) trims nothing, where a comment on a spanned
   change paints a target over the change's span and repaints its line boxes as the float's Comment does
   (md-config-paint-presel-retrim-browser.test.ts, the real panel at 300 to 600 px, the whole item and four of its
   links: no padding-only mark and no bare blank pending or after Cancel, the marks a paint pass's under the same
   target; md-config-paint-presel-kinds-browser.test.ts: zero Range measurements for the kinds that paint no target,
   where round 14 measured 4,260 on the 5,000-link paragraph, 22 to 27 ms a click, and one trim with measurements on
   each open and Cancel of a comment on the spanned insertion;
   md-config-paint-presel-scope-browser.test.ts, round 16: two overlapping comments at 300 and 800 px, a comment
   across two paragraphs with the target in the second, an insertion and a deletion point in a paragraph the target
   never touches, and a target on the embed chip's text at 385 to 725 px, the nesting, the click target and the marks
   the pass's pending, after Cancel and after the next pass); and what the repaint painted again it re-files as the
   pass does (a change whose every mark the trim removed as not shown, one whose mark stands again as shown, a
   highlight whose every mark went as not painted) and renders the cards in the same call when a filing moved, since
   the callers after a passage's Comment and after Cancel render the composer alone and the cards read the filings at
   render time (round 17: a session's insertion of one soft hyphen, a character the index records and the trim
   measures, rendered as a hyphen at a line break and as nothing elsewhere, so the target's padding moving the
   paragraph's wrap point across it moved the filing at every open and Cancel while the card said the opposite until
   the next render; a plain space never reaches the shape, since the index skips whitespace and never paints it;
   md-config-paint-presel-refile-browser.test.ts, both directions over the real panel, the paragraph in the generic
   monospace face at a 60ch measure so the wrap point is the design's and not the face's). The repaint's price is a
   fresh paint of the boxes' marks to the fixpoint, one layout a pass, in the real pane at 1000 px: the fourteen-link
   item 5 to 6.5 ms an open and 2.2 to 2.5 ms a Cancel, the 120-link item 27 to 39 and 14 to 22 ms, forty comments
   over sixty paragraphs 3 to 5 and 1.4 to 1.7 ms; one comment across the paragraph of 5,000 links 6.0 to 6.2 s an
   open (three passes, 13,821 Range.getClientRects calls) and 3.2 to 3.3 s a Cancel (two passes, 9,510), against 2.7
   to 2.8 and 1.3 s for round 14's trim of the standing marks and about 1.3 s for main's untrimmed paint, recorded
   beside the paint's cost below and not optimised (the passes are the fixpoint's). The panel does not repaint on a
   reflow, a load or a face's arrival, so a blank trimmed at the old layout that renders at the new one stays bare
   until the next paint pass (item 10). The re-trim's price per reflow: realistic shapes under 10 ms (200 comments
   over 300 paragraphs 0.6 to 1.2 ms, a 120-link item 0.6 to 11 ms); one comment across the 5,000-link paragraph 1 to
   13 s in the real pane under the convergence loop (round 14's measurements, three runs agreeing on every call count:
   a window-resize step 1.0 to 1.1 s, a divider release 2.1 to 2.4 s narrowing 1000 to 700 px and 5.1 to 5.6 s
   widening back, a text-size step 12.4 to 13.3 s over ten passes, nine that unwrapped and the tenth confirming, each
   pass after one that unwrapped laying the mutated paragraph out again at 1.0 to 1.3 s a layout; round 13's 1.5 to
   4.6 s was measured under the three-pass cap the same round replaced, which left 51 padding-only marks on the
   text-size step where the loop leaves none), recorded beside the paint's cost below and not optimised. The divider's
   drag itself fires one reflow, at release (the shell moves a ghost line and lays the pane out once); a window-edge
   resize reflows every frame and pays the price per frame. The cost, measured on the build box in headless Chromium
   under feed.css at 800 px: one comment across a paragraph of 5,000 links (4,999 blank marks, 324 wrap points) paints
   trimmed in 300 ms against 269 untrimmed once the layout the panel reads next is counted on both sides (323 against
   45 measured alone, the difference being that layout), two passes of 9,674 Range.getClientRects calls in all, 324
   marks unwrapped, one per line break of the painted paragraph; a 200-comment pass over 300 paragraphs 21.1 ms
   batched against 20.3 untrimmed and 20.6 unbatched, Chromium laying the mutated paragraph out incrementally, so the
   batching bounds the cost rather than saving much here. In node the stand-ins offer no layout, so the trim measures
   nothing and the node tests pin the DOM shape and the two skips: md-config-paint-trim.test.ts over a stand-in that
   measures (the rule, the hidden-ancestor guard, two-phase as one layout per pass, the fixpoint to convergence, a
   five-blank cascade unwrapped whole with one layout per pass, every pass over the marks the last one kept and a
   confirming pass when candidates remain, the batching option, the candidate alphabet, the root guard and the
   pre-skip), md-config-paint-trim-fixpoint.test.ts (round 13, over a stand-in whose Range reads an element the Range
   selects whole as its box, as CSSOM does: the cascade to convergence and TRIM_STATS, the safety cap, a nest of marks
   measured by its text and dropped in one pass, the pre exemption of the pre-skip),
   md-config-paint-collapsed-blank.test.ts (no top-level mark, no empty mark, the content marks exact, unpaint and
   repaint exact, over 66 scenes plus the top-level zero-width one, with pointers and on the index path) and
   md-config-blank-scenes-fixture.test.ts (the union fixture's shape: the two paragraphs in every scene, a CR always
   the CRLF pair, since a lone CR had split a scene's html block and left it exercising nothing). The browser legs pin
   the trimmed result over the union of every blank scene rounds 7 to 13 collected
   (anchor-map-fixtures/blank-scenes.json, 95 scenes: folds, an author's figure, details, dl and center, badge rows,
   br pairs, wrap points at several widths, nbsp and U+3000, U+FEFF, every zero-width character of round 11's
   alphabet, the bidi marks and the soft hyphen, svg icons, audio with and without controls, an author pre with br and
   block children and with spaces or a tab between its block children, tables, footnote definitions, list items, a
   form feed, a CRLF, a floated image, a picture without an image, a space inside a kbd, a table caption, a plain
   note): md-config-paint-trim-browser.test.ts (the trim removes blank marks alone, no padding-only mark at any depth
   of nesting, the oracle reading the text nodes under a mark, every rendered blank of the painted blocks marked
   wherever the trim unwrapped nothing and the paint reaching the closing paragraph in every scene but the recorded
   refused one, no top-level mark, the unpaint exact, the plain note untouched, one comment and two comments across
   the passage; the wrap scenes at eight widths from 800 to 180 px; the reflow re-trim; the 200-comment pass batched
   within a same-run bound of the untrimmed one; the oracle's own check over a hand-built nest),
   md-config-paint-trim-panel-browser.test.ts (the real viewer and panel: the batched pass, the reflow, a text-size
   step; four and eight overlapping comments nested one level per comment with no padding-only mark at any level,
   fresh at 300 px and after a narrowing), md-config-paint-trim-fixpoint-browser.test.ts (the 120-link item and the
   5,000-link paragraph at 800, 700, 500, 400 and 300 px, fresh and narrowed from 800 px with one re-trim: no
   padding-only mark, no call at the safety cap, the paragraph's cascade past three passes; one to eight overlapping
   comments at 300 px; the pre scenes, every rendered blank under the pre marked),
   md-config-paint-retrim-events-browser.test.ts (the real panel: a figure's load and a font face's loadingdone
   re-trim with no reflow, a change of one zero-width space filed as not shown with Reveal, a paint made in a hidden
   pane re-trimmed on the show: in the same task by the frame the hidden trim armed, leg 4, and across frames by the
   seam's reflow report with the trim twice per event while hidden and never per frame, leg 5),
   md-config-paint-presel-retrim-browser.test.ts (rounds 14 and 15, the real panel: the whole item and four of its
   links selected over the item's comment at 300, 400, 500 and 600 px, the float's Comment then Cancel; no
   padding-only mark of either class and no bare rendered blank in the item while the composer is pending or after
   Cancel, the target's marks nested inside the highlight's and never the inverse, the marks a paint pass's under the
   same target and the highlight's blank marks after Cancel the pass's before the click, the seam reporting neither a
   paint nor a reflow), md-config-paint-presel-kinds-browser.test.ts (round 15, re-aimed by the merge of fork PR #657:
   the real panel over the 120-link item's comment, a spanned insertion's card and a deletion's card; Comment on this
   file, Reply on the comment and Comment on this change on the deletion's card, by id alone, each opened and
   cancelled with zero Range measurements and zero trims, where the float's Comment on eleven of the links and Comment
   on this change on the spanned insertion's card, a target over the inserted word, each trim once with measurements
   on open and once on Cancel), md-config-paint-presel-scope-browser.test.ts (round 16, the real panel:
   two overlapping comments whose order by time is not their order in the text, at 300 and 800 px, keep the pass's
   nesting, click target over the overlap and ring of marks while the composer stands, after Cancel and after the next
   pass; a comment across two paragraphs overlapped in the first by a later one keeps them with the target in the
   second; with the target in the other paragraph an insertion inside the highlight opens the change on a click and a
   deletion point stays inside one highlight mark; a target on the embed chip's text at 385, 500, 605 and 725 px
   repaints every mark of the paragraph's highlight, its blank marks and the paragraph's bare blanks after Cancel the
   pass's before the click and pending a pass's under the same target), md-config-paint-presel-refile-browser.test.ts
   (round 17, the real panel: a session's insertion of one soft hyphen in the target's paragraph, rendered as a hyphen
   at a line break alone, so the target's padding moves the paragraph's wrap point across it and the change's filing
   with it; the paragraph in the generic monospace face at a 60ch measure so the wrap point is the design's and not
   the face's; in both directions the change card's tag, Reveal and link follow the body while the composer stands,
   after Cancel and after the next pass, and a pass under the same target files the change as the repaint did),
   md-config-paint-collapsed-blank-browser.test.ts (every whitespace-only node held across the paint and read node by
   node: a mark exactly when it renders with a width), md-config-paint-whitespace-browser.test.ts leg 4 (the
   5,000-link paragraph: one blank mark unwrapped per line break at 800 px, no zero-width blank mark, no rendered
   blank unmarked, the passes read off the getClientRects and removeChild calls, the first over every blank mark, each
   later one over exactly the marks the last kept, ending in a pass that unwraps nothing or in no candidate left, at
   800 px and at 700 px, where the cascade takes eight passes, with no zero-width blank mark at either, the trimmed
   paint within a same-run bound of the untrimmed one) and md-config-paint-rendered-space-browser.test.ts (a form feed
   leading a block renders a 14 px glyph inside the mark where the bare node collapses, so the highlighted paragraph
   shows the glyph; item 10). History, for the reader of the rounds' records: main skipped any whitespace-only node
   under one of twelve block containers (UL, OL, LI, BLOCKQUOTE, DIV, TABLE, THEAD, TBODY, TR, SECTION, ARTICLE, BODY;
   TD never among them, which is why the `&nbsp;` spacer cell painted on main) whatever its neighbours, so the
   rendered space between two inline children of a list item or a centred badge row was never painted and the ring
   broke at it, and it painted every other blank as a ringed box around nothing. Round 8 read the node's neighbours
   (the "\n" between a folded callout's paragraphs, DETAILS not being on the list); round 9 derived BLOCK_BOXES, read
   a block-box parent's edge and a `<br>` as a line edge, and made the neighbour reads constant time over the DOM's
   sibling pointers (one mark across 3,000 links 850 ms indexed against 32 with the pointers;
   md-config-paint-whitespace.test.ts counts the child-list reads and its browser leg times equal work); round 10
   restricted the readings to the collapsible five and retired main's container list
   (md-config-paint-rendered-space.test.ts and its browser leg); round 11 read each side's rendered content through
   empty inlines, hidden elements, atomic inlines and text ending in a space, and skipped a zero-width run wherever it
   stood. Round 12's fresh reading found the next shapes that prediction got wrong (an inline svg looked past as
   rendering nothing, an audio element without controls read as a box, a floated image, a picture without an image, a
   form feed read as collapsible, the bidi marks and the soft hyphen outside the zero-width alphabet, a space inside
   an inline-block, and the line wrap no reading of the DOM can see), and the prediction gave way to the trim: the
   repo's rule is an exact mechanism over a heuristic that approximates it, and the exact answer is the browser's own
   layout. A passage that is one zero-width character alone still gets a card and no highlight (its one mark is
   trimmed and paintRendered returns null; md-config-paint-collapsed-blank-browser.test.ts).
   anchor-map-obsidian.test.ts and the browser leg select across the formula and get the TeX between. The fill's two
   fallback shapes, KaTeX's `span.katex-error` on TeX it cannot parse and the belt's `code.md-math-src` past a bound,
   are controls like `.katex` (anchor-map.ts FORMULA_CLASSES), so a display fallback keeps the 1:1 pairing and an
   inline one maps around; before that a display fallback took no element and every block after it paired one early,
   and the reader's place was a block off (the review round 1). The control list keys on class tokens the sanitizer
   lets an author write, as Slice 3's `code-copy` did: a hand-typed span wearing `katex`, `katex-error`,
   `md-math-src`, `md-fnback`, `md-frontmatter-head` or `fv-gate` is a control too, its text skipped, so a quote
   covering it is refused with the Raw view offered while a comment on the prose beside it paints (Slice 1's note
   records the shape for the math markup); the collision is tolerated, as item 9's is, since only the fills could mark
   their own elements and marked's renderer emits `md-fnback` and `md-frontmatter-head` before the sanitizer (the
   review round 7). reader-place.ts also keys its list on class tokens, but on five of these seven: the two fallback
   shapes are not skipped there on purpose, since an html block's fallback can only come from a placeholder the author
   typed, whose TeX the source parse reads too (its header; the review round 8). A selection endpoint inside a
   formula's glyphs is the formula touched ("touches a formula", the Raw view offered at the formula's line); the edge
   that selects none of it maps the prose beside it; an endpoint inside another control (a back link's label, the fold
   label, a gate's label) stands at the control's edge, so a triple-click on a footnote definition maps its words
   (anchor-map-obsidian.test.ts tests 8 to 11, md-config-math-map-browser.test.ts). The block tokenizer's start hint
   names only a newline before a line the tokenizer will accept (math.ts nextBlockMath, one pass with a memo of the
   first closer per family, its answer remembered per lexer frame by md-block-start.ts): marked clips the paragraph at
   the hint and resumes it when the tokenizer says no, with a newline the source did not hold, so a rejected line
   (`$$x$$ is inline here.`, an unclosed `$$`) broke the raw tiling from that paragraph to the end of the note, and a
   match at the string's own start, one character into a line, cut `A $$x$$` in two
   (md-config-math-block-start.test.ts, whose bound holds the hint to one pass per call: a first cut that ran the
   block tokenizer at every candidate lexed a note of 1,500 rejected candidates in 13 s and never shipped). marked
   also joins two paragraphs its own regex separated (a header-looking line over a delimiter row with a different cell
   count, a lowercase `<prefix>` line, a bare `* ` or `1. ` bullet, each interrupting the paragraph and then refused
   by its tokenizer) whenever a block hint has a hit anywhere later in the note, with a newline in the raw the source
   does not hold; and with no hint at all it joins a paragraph and an indented line under it that a
   delimiter-row-shaped line or a `---` follows (the gfm table interrupt admits any indentation on its header line,
   the code tokenizer runs before the table's and takes the indented line, and the lexer joins it onto the paragraph
   with the indentation gone from `text`, CommonMark's own reading of a continuation line), at the top level, in a
   quote's body and in a list item's block text. The anchor map rebuilds such a paragraph's source lines from its raw
   and text (each text line the raw line it came from less up to four spaces, a blank raw line no text line matches a
   join's newline; anchor-map.ts sourceRaw and joinedSourceRaw, in the block table and the walk) and maps the text
   into them line by line through the suffix view, so either join costs the map nothing (the review rounds 2 and 3 for
   the hint's join: before it every block from the join to the end of the note refused; round 5 for the indented
   line's, pre-existing at the base, where the round-3 placement by `text` alone stopped at the first stripped space
   and every later span collapsed alike; md-config-merged-paragraph.test.ts,
   md-config-merged-paragraph-browser.test.ts). The joined rendering, one `<p>` where bare marked gives two, is
   marked's own and GitHub's for those shapes, and it turns on a `$$` further down the note (item 10). marked calls
   every block hint before every paragraph on the whole remaining source, so a hint that scans the rest of the note
   made the lex quadratic in the paragraph count (the review round 2: 8,000 one-line paragraphs 1.3 s on the singleton
   against 34 ms with no hint, a 200 KB reply twice the base's time); the math hint's answer is remembered per lexer
   frame (md-block-start.ts memoBlockStart, exact because a frame's sources are suffixes of one another and a nested
   body is a frame of its own; the callout's hint, memoised the same way in round 2, is gone since round 3, item 5),
   the math tokenizer's closer search too, and the lex is linear in the paragraph count: 36 ms for those 8,000
   paragraphs, 35 ms for 8,000 rejected `$$` lines where the base took 736 (md-config-block-start-memo.test.ts holds
   the memoised lex equal to the plain one and the singleton's lex linear: since the review round 8 as the median of
   seven paired ratios of one lex of a 16,000-paragraph note to eight lexes of a 2,000-paragraph one, equal work for a
   linear lex, bounded at 3 where a linear lex measures 1.0 to 1.1 and the pre-memo one 7.5, with a 1,500 ms guard on
   the large note's median, and the math hint's own finder counted once per frame through the frame it writes; round
   7's single-lex pairs, bounded at 24 where a linear lex measured 9, inflated three times under a CPU quota, steadily
   across every pair, because only the large lex outlasted a scheduler slice, and the earlier bound, ten times a small
   timing taken first, failed under a parallel suite's load on the merge audit). KaTeX's flagged text takes a theme
   token, `--math-err` (math.ts MATH_ERROR_COLOR, which KaTeX writes into the span's inline style), declared in both
   theme blocks of both sheets at 4.5:1 or better on `--bg`, overridden to black in the print block on `.fileview-md`
   (a custom property inherits, so it reaches the flagged span and an unsupported command's glyphs inside a rendered
   formula alike; set on `.katex-error` alone, those glyphs printed in the screen red) and to the bubble's own ink in
   the person's bubble (`currentColor`: the page's red read at 1.67:1 and 1.28:1 on the two fills; the review round 2,
   md-config-math-inks-browser.test.ts), as the source fallback prints; KaTeX's default #cc0000 read at 2.8:1 on the
   dark page (md-config-math-error-colour.test.ts, theme-parity.test.ts). The heading ids are minted BEFORE the fill,
   as sanitizeMd's caller pass (file-view.ts mintHeadingIds, md-sanitize.ts `own`): read after it, `# Ratio
   $\frac{a}{b}$` slugged KaTeX's glyphs in layout order (md-ratio-ba) where GitHub's slug and the note's own links
   spell md-ratio-fracab (md-config-fragment-landing-browser.test.ts). The Web Worker of the design note is NOT built:
   VS Code's webview CSP has no `worker-src`, and an asynchronous fill changes when `fireRendered` and the seat run
   over a paint (the comments panel and the reader's place would meet placeholders); the synchronous bounded fill of
   Slice 1 stays, and the note stays a direction.
3. *Front matter* renders as ONE element, `details.md-frontmatter` with a `summary` reading "Front matter" and the
   YAML in a `pre`, escaped text and never author HTML. The tokenizer fires only for the document's first token
   (`tokens === this.lexer.tokens && tokens.length === 0`: a quote's or a list item's body is lexed into a fresh
   array, so `> ---` inside a quote stays an hr; `state.top` is not that test), and only for a body that reads as a
   YAML mapping (isYamlMapping: every left-margin line a `key:` line, a `- ` item under a key, a `#` comment or blank;
   a bare key begins with a letter or digit of any script, or an underscore, since ASCII alone rendered a vault whose
   property names are in its own language, `Über:`, as the hr and the heading again: the review round 3) with no blank
   line after the opener (pandoc's rule), so a document that merely opens with a rule, a fence opening with `---` or
   prose between two rules keeps its blocks (the review round 1: a reply bounded by rules folded its first section
   into a closed block, and a `---` inside a fence closed the block early, so the fence's closer opened a block that
   swallowed the rest). Its raw tiles the source from offset 0, trailing blank lines included, so the block table's
   first span is `[0, 37]` where it was `[0, 3]` and `[4, 37]`, and the setext h2 the keys used to become (with its
   minted `md-title-...` id) is gone. anchor-map.ts treats it as a hole block ("the front matter") with the fold label
   a control; `tagOf` gives DETAILS. md-config.test.ts renders it (one element at the start, none mid-document or
   inside a quote; the rule-bounded, fenced and YAML shapes); anchor-map-obsidian.test.ts holds the block span from
   offset 0, the DETAILS tag, the hole's reason and the hr-without-YAML case. A fold's state survives every paint:
   renderBody notes every `details` under `.fileview-md` before the swap and restores each after it, in both viewers
   (file-view.ts foldKeeper; before it the Rendered/Raw switch, a reload's landing, the editor's take and handback and
   a `#` reveal reset every fold to what the source says; the review round 2, md-config-fold-state-browser.test.ts
   drives the gestures over the real Files bundle). The match runs in two passes, each in document order: first by
   class, summary text and body text, when that exact key names as many noted folds as new folds, the k-th new paired
   with the k-th noted (the review round 4: two identical `> [!note]- Todo` placeholders shared one exact-key queue,
   so a session filling the first while the person read the second swapped their states; a key whose count changed, a
   twin filled in, added or removed, falls whole to the second pass and its order, which hands the first noted state
   of that title to the first new fold of that title, so the twin the person reads keeps its state through a fill
   anywhere and through a twin added or removed behind it; a twin added or removed AHEAD of it shifts its state by one
   (an identical one, whose arrival or departure changes the key's count; a same-titled fold with a body of its own
   leaves the twins paired in the first pass while their count stands; once it changed, one removed or added ahead of
   them in the same write shifts their states the same way, the review round 7): three identical `> [!note]- Todo`
   twins, the middle one open, the first removed, and the person's twin is now the first, takes the first noted state,
   shut, and the one below it opens, the content having nothing to tell identical twins apart, the limit the review
   round 6 states here and in foldKeeper's header; the review round 5: round 4's rule, one noted fold and one new fold
   only, sent untouched twins whole to the second pass too, where a same-titled fold inserted or removed ahead of them
   shifted their states by one, the fifth leg of the fold-state test), then the leftovers by class and summary text
   alone, so a fold a session's edit rewrote keeps its state and a fold that stands as it was keeps its own when a
   fold of the same class and title was removed or inserted ahead of it (the review round 3: with class and summary
   text as the whole key, two `> [!note]- Same title` callouts shared one queue, and a reload the Comments panel's
   poll asked for after such an edit opened the fold the person had left shut; the same leg drives that reload through
   the panel's poll). Order alone decides an edit that both removes one same-titled fold and rewrites another's body,
   a twin rewritten in the same write that inserts a same-titled fold, whose text change is the insertion's, and an
   identical twin added or removed ahead of the twin the person reads. A body of `#` lines alone is a comment-only
   mapping and folds, as pandoc, Jekyll and Obsidian read it; in a reply that shape is inside item 1's open ruling.
4. *Footnotes*, our own extension (marked-footnote is not installed and renders at the end, which breaks the 1:1 block
   pairing). `[^id]` renders `sup.md-fnref > a[href="#fn-id"][id="fnref-id"]` showing its number, and ONLY when the
   document defines the id (GitHub's rule; the lexer lexes every block before any inline text, so the definitions are
   known when a reference is lexed): `[^1]` with no `[^1]:` line stays as written, where it rendered a live-looking
   link to nowhere (the review round 1). A second reference to the same note gets `fnref-id-2`. A definition renders
   IN PLACE as `div.md-footnote[id="fn-id"]` with a back link `a.md-fnback[href="#fnref-id"]` first, one element per
   definition, so the paragraphs after it pair as before (the acceptance); its body is a paragraph inside the div, the
   back link first in it (GitHub's `li > p`, since the review round 10: rendered directly under the div, the spaces
   between the body's inline elements were whitespace-only text nodes under a DIV, which the paint's container rule of
   the time skipped, so a highlight across `[^1]: **a** *b*` or two links in a definition broke at each space, a 4 px
   gap, where main, rendering the line as a plain paragraph, painted it whole; both sheets give that paragraph no
   margin of its own, so the footnote's box is unchanged, measured to the pixel; md-config-footnote-paint.test.ts and
   its browser leg drive paintRendered from the paragraph before to the paragraph after); its text runs as far as
   marked's paragraph rule reads a paragraph, so a lazy continuation line (GitHub's form) or a two-space indented one
   (Obsidian's) stays in the note and another definition, a list, a heading or a line a registered block extension's
   start hint names ends it (a four-space rule lost a wrapped definition's second line; md-config.ts clipAtBlockStarts
   applies the cut marked makes before its own paragraph, so a `$$` block on the line after `[^1]: text` is a display
   formula after the note, where the borrowed paragraph rule ran over it: the review round 2). Block content inside a
   definition, GitHub's four-space form (a fence, a list, a second paragraph indented four spaces), is not adopted: a
   four-space-indented line is the paragraph's continuation, as marked's own paragraph reads it, so an indented fence
   renders as a code span (the review round 3, open in item 10). A duplicate definition keeps its class and back link
   and drops its id, so `#fn-id` lands on the first. Numbering is by order of first reference, kept on the lexer
   instance (one per parse, the anchor map's static lex included), and a definition nothing refers to shows its marker
   as written (`[^id]:`) as a label with no back link, so every character the author wrote stays in view: a regex
   class explained at a line start, `[^a-z]: matches anything but a lowercase letter`, is GFM's definition shape,
   which GitHub drops whole, and the bare id ran into the text as a word (the review round 2). The ids reach the DOM
   prefixed `user-content-` and the `#fn-id` hrefs land through fragmentTarget in the viewer
   (md-config-obsidian-browser.test.ts clicks both ways over the Files bundle) and the chat's `#` delegate. A `[^n]:
   URL` line is a footnote now, where marked's `def` rule used to swallow it as a link reference (a note that used
   that form as a real link reference changes rendering). The shown number is a hole ("a footnote reference"); the
   back link is a control; the definition's text maps past its marker through the blockquote's suffix view. `tagOf`
   gives DIV. md-config.test.ts renders the reference, the in-place definition, the numbering, the URL-only
   definition, the undefined reference, the duplicate, the orphan and the continuation lines;
   anchor-map-obsidian.test.ts holds the DIV tag, the paragraph after a definition, the definition's own text and the
   number's refusal.
5. *Callouts.* A block extension tried before the built-in blockquote: GitHub's `[!NOTE]`, `[!TIP]`, `[!IMPORTANT]`,
   `[!WARNING]`, `[!CAUTION]` and Obsidian's `[!type] Title` with any type render `blockquote.md-callout` with a
   `p.md-callout-title` (the author's title, else the type capitalised) and the body lexed as blocks; `[!type]-` and
   `[!type]+` render a `details` closed or open with the title in its `summary`. Its extent is marked's own blockquote
   rule, borrowed, so a lazy continuation line with no `>` stays inside the tinted block as GitHub keeps it, and it
   registers NO start hint (the review round 3): its marker line begins with `>`, a paragraph interrupt marked's own
   rule knows, so a hint could shorten no paragraph, and the one round 1 gave it (after a newline only, since marked
   calls a hint on `src.slice(1)` and a `^` alternative cut `a> [!note] b` into a one-letter paragraph and a callout;
   round 2 memoised its answer per frame) set marked's clip flag for a `> [!` anywhere later in the source, which
   joined a paragraph and its interrupt-rejected successor into one `<p>` with a raw that no longer tiled the source
   (item 2). The marker line is spelled as marked spells a quote's, `>`, an optional space or tab, then up to three
   spaces before `[!` (round 3: one space alone left `>\t[!NOTE]` and `>  [!note]` plain quotes where GitHub reads the
   alert). The body takes marked's two blockquote preparations: the marker's optional space may be a tab (`>\tbody`
   kept its tab and the nested lex made it indented code) and a lazy `===` or `--` line is prefixed with four spaces
   so it stays a paragraph's text and not a setext underline (the review round 2), from the body's second line on: the
   body's first line has no paragraph before it to underline, and guarded it was indented code reading `===` (round
   3). The body's marker is CommonMark's, a `>` after at most three spaces, where marked's blockquote strips a `>`
   under any indentation (` *>`): a lazy continuation line indented four or more spaces that begins with `>` keeps its
   `>` as text in a callout, as commonmark.js and GitHub render it, and loses it in marked's plain quote (the review
   round 5, kept as built: the callout follows GitHub and the anchor map's suffix view holds either way, since round 6
   for the bare tail form too, a lazy `>` line indented four or more spaces closing the quote, which refused the quote
   whole until then, below; md-config.test.ts pins both). The anchor map's suffix view reads through those four
   spaces, which hold no source position, so the body line and its underline map to their own characters
   (anchor-map.ts suffixLineView; before, the callout or the quote refused whole with a reason naming a tab; round 3,
   anchor-map-obsidian.test.ts). The same view takes a quote's empty `>` line past the text as blank under ANY
   indentation (QUOTE_BLANK_RE, marked's own strip ` *>[ \t]?`: a lazy `    >` or a tab and `>` enters the quote
   through the paragraph's continuation and the strip empties it there too, so the quote's own ` {0,3}>` opens a line
   and is not what the tail rule reads; round 6, where a closing `>` indented four spaces refused the quote whole and
   one indented three mapped): marked's blockquote tokenizer strips the marker and rtrims the newlines left, so a
   quote closed with an empty `>` line, a common way to write one, has a raw line more than its text and refused whole
   from Rendered, its nested and list-hosted forms too, where a callout of the same shape mapped (round 5,
   pre-existing at the base; anchor-map-obsidian.test.ts, test 17 holding the indented shapes). The nested walk runs
   over the tab-expanded text (anchor-map.ts blockLexView; normalizeSource shares the expansion through expandTabs): a
   blockquote's text, a callout's body and a list item's text go through marked's block lexer again, which expands
   their leading tab runs before lexing, so the nested tokens' raws did not tile the unexpanded text, and a quote
   closed by `> ` and a tab or `>` and two tabs (the strip takes ONE whitespace after the marker), a `> ` and tab
   continuation line, `>` and two tabs before a line of text, a callout body line with a tab after the marker's space,
   and the list holding a `- ` and tab item all refused whole with the paragraph reason or a reason naming the tab;
   they map since round 6, each tab's four spaces taking the tab's position so no emitted character moves, and an
   indented code block a tab opens is a hole at the tab (a `> ` and tab line of its own paragraph, a `- ` and tab
   item's text). The pre-slice refusal of a tab after the marker is retired with it, pre-existing at the base
   (anchor-map-obsidian.test.ts test 18; anchor-map.test.ts's two pre-slice pins hold as the code hole and as marked's
   three-space bullet mismatch). The type rides in a class (`md-callout-note`), not the `data-callout` attribute the
   design named, since the sanitizer drops every data attribute; the sheets tint by class through the page's own
   tokens (note and its kin the accent, tip green, important teal, warning amber, caution red, any other type the
   hairline; feed.css's `:root` declares the awaiting green and the compacting teal the tip and important tints read,
   which stood in its light block alone, so on the two dark themes the feed page's tip and important callouts lost
   rail, wash and title tint: the review round 2, feed-css-vars.test.ts reads the sheet with the light block cut out
   and md-config-feed-callout-tints-browser.test.ts six callouts under both sheets and three themes). The tip and
   important tints are tokens of their own since round 5, `--callout-tip` and `--callout-important`, declared in both
   theme blocks of both sheets: on the dark themes the awaiting green and the compacting teal as before; on the light
   theme the light `--green` (#3E7D0E, 4.25:1 on the page) and a teal (#0F766E, 4.59:1), since the status fills, the
   same hex in both themes, were 2.27:1 and 2.09:1 rails on the cream page, under the 3:1 non-text floor, and the rail
   and the wash are the type's one carrier; md-config-callout-title-ink-browser.test.ts holds the five alerts' rails
   at 3:1 on the page under both sheets and the three themes, theme-parity.test.ts both tokens at 3:1 on `--bg` in
   both themes, and the feed-tints leg and feed-css-vars.test.ts read the new tokens. The title reads in the body's
   ink, bold, and the type shows on the rail and the wash alone (the review round 3): the tint tokens are rails and
   fills, not inks (the hairline at 1.45:1 and the caution red at 2.91:1 on the dark themes, the light theme's tip and
   important under 2.2:1), so a title in the rail token failed every custom type;
   md-config-callout-title-ink-browser.test.ts holds every title at 4.5:1 under both sheets and the three themes, and
   the bubble's title reads in the bubble's own ink (item 1). The title line is a hole ("a callout's title", since the
   marker is not shown and a missing title is generated); the body maps as blocks. `tagOf` gives BLOCKQUOTE, or
   DETAILS for a folded one, whose open or closed state survives a paint (item 3, foldKeeper). The folded form wears
   the blockquote's `margin: 0.5em 0` since round 6, at the blockquote rule's own weight through a `:where()` head, so
   a fold that is the body's first or last child keeps the body's edge as a blockquote does (a details matched no
   margin rule, and a run of `> [!tip]-` folds stacked flush into one tinted box with a notch where their rounded
   corners met; both sheets, a fileview-parity head; md-config-chat-styles-browser.test.ts reads both forms' margins
   in a reply, a notice, the viewer root and the bubble, and two one-child roots at 0px). A `#` target inside a folded
   callout, a closed `details`, is revealed before the scroll (md-sanitize.ts revealFragmentTarget, the HTML spec's
   ancestor revealing steps, run by scrollToFragment for both viewers; before it the click scrolled to nothing with
   the fold shut). The comments panel runs the same reveal on its own marks before every scroll to one
   (file-comments.ts revealMarks: goTo, scrollCard and the head click's centering, the margin pass re-run after a fold
   opened), so a comment on a folded callout's body or on the front matter shows its highlight where a shut fold came
   to the center with none (the review round 2; md-config-goto-closed-details-browser.test.ts). md-config.test.ts
   renders the five alerts, a titled type, the two folds, the lazy line and the mid-paragraph marker;
   anchor-map-obsidian.test.ts holds the tags, the body's blocks (a folded one's hidden body too) and the title's
   refusal, the generated title included; md-config-fragment-landing-browser.test.ts lands a heading link, a
   `[[#Heading]]` wikilink and a footnote reference inside a shut fold.
6. *`==mark==`* renders `<mark class="md-mark">` and maps by delimiter width like em and strong; the opener must touch
   its content, so `a == b` in prose stays literal, and neither delimiter may touch a word on its outside (the run of
   `=` is exactly two; the opener is refused after an ASCII letter, digit, underscore, closing bracket, quote or `=`,
   the characters an operand ends in, and the closer before an ASCII letter, digit, underscore or `=`, which a right
   operand begins with; ASCII only, so CJK prose with no space around a highlight is not refused), so `a==b and c==d`,
   `a===b`, `len(a)==0 or len(b)==0`, `x[i]==y[j] and a[0]==b[0]`, `'a'==b and 'c'==d` and `f()==1 and g()==2` in a
   sentence or a heading stay literal where the plain delimiter rule paired two comparisons into one highlight (the
   review round 1 guarded the opener against letters and digits, round 2 both ends against an operand). A highlight
   holds no `==` (the review round 3): the first `==` after the opener is its closer, and a closer that touches a word
   makes the text literal up to it, so `==high==lighted and ==more== end` highlights `more` alone and `if x ==0 or y
   ==1 then ==done==` highlights `done` (round 2's lazy match ran on to the next `==` and rendered one highlight from
   `high` to `more`, the second opener eaten); `==a == b==` is literal, the operator reading winning as everywhere in
   the rule; the recorded consequence stands, `==high==lighted` alone is literal. A code span inside a highlight is
   skipped whole (the review round 4): the tokenizer matches over a copy of the source cut at the first `==` outside a
   code span, with the spans before it masked to marked's own filler (md-config.ts markView), so `==see `a==b` here==`
   highlights `see a==b here` with the comparison in code, as Obsidian renders it, and a `==` inside a span never
   closes the highlight (`==x `y== z` w==` is one highlight, where rounds 2 and 3 closed it at `y` and broke the
   span); only a code span is skipped, so `==**a==b**==` stays literal, and the double-tilde rule keeps the blind spot
   its two copies always had. A backslash-escaped `=` is the highlight's text (the review round 5): marked masks
   escaped punctuation before its em and strong run and hands an extension the unmasked source, so `==a \== b== end`
   closed at the `==` of `\==`, highlighted `a \` and left ` b== end` literal, where `\=` is marked's escape
   everywhere else in the paragraph; a backslash and the ASCII punctuation character after it are one atom of the
   content, CommonMark's escape (its section 2.4), and a backslash before any other character is a literal backslash,
   text of the highlight (the review round 6: round 5's atom took a backslash and ANY character, so `==a \ == z`
   rendered a highlight ending in a backslash and a space where round 4 and Obsidian leave it literal, its closer
   preceded by whitespace; a backslash before a space, a tab or a newline is text and the whitespace stands as the
   content's last character, which refuses the closer, while `==C:\dir== x` highlights as it always did); the view
   skips a `==` an odd count of backslashes precedes, so `==a \== b==` highlights `a == b`, `==x \\== y` and `==a\\==
   b` close at their `==`, two backslashes escaping each other, and `==a\==` is literal, one `=` escaped and one left;
   the double-tilde rule keeps the blind spot marked's own gfm del has. md-config.test.ts pins the shapes and the cut.
   The element's class is what both sheets' rule keys on, `mark.md-mark` (a bare `.fileview-md mark` outranked the
   comments panel's single-class marks, `.fc-hl`, `.fc-presel` and `.fc-ins`, so every highlight in the Rendered view
   wore the amber wash: round 3, md-config-mark-classes-browser.test.ts compares the panel's marks inside the view
   with the same marks outside it, and md-config-math-map-browser.test.ts reads their dress on the real fill).
   md-config.test.ts renders it and keeps the comparisons literal; anchor-map-obsidian.test.ts maps its text by the
   delimiters.
7. *Decision 2, wikilinks and embeds.* The renderer emits an anchor ONLY when the per-parse walkTokens of the file
   kind (file-view-links.ts viewerWalkTokens, run by mdBlock for the file kind alone) stamped the token `resolved`:
   `[[Note]]` becomes `<a href="Note.md">Note</a>` (`.md` appended unless the target names a file type Obsidian opens,
   KNOWN_EXT_RE: `[[img.png]]` and `[[paper.pdf]]` keep their extension, and a dotted title such as `[[Note.v2]]`,
   `[[Release v1.0]]` or `[[Node.js]]` is a note, where any dotted target read as a file with an extension and linked
   a file that does not exist; the review round 1), `[[Note|alias]]` shows the alias, `[[Note#Heading]]` carries the
   fragment, `[[#Heading]]` is a section link of the same note; #347's link pass then turns each into a path link to
   `<dir>/Note.md` with the fragment in `data-frag`, no existence check. Everywhere else (a chat reply, a URL
   document) the same text is `span.fv-wikilink.fv-dead` showing the source as written, brackets included (`[[Note]]`,
   `![[img.png]]`, an R-style `matrix[[0]]` too), with a title that says why and names no surface (the review round 1:
   the span showed the alias or target alone, so a reply's reader could not tell a wikilink from plain text, and its
   title spoke of "the viewer" to a reader of a reply). `[[text]](url)` is CommonMark's link with bracketed text and
   `![[img.png]](url)` its image: the tokenizer yields when `]]` is followed by `(` and marked's link rule reads the
   span, as GitHub renders them (the review round 2: the wikilink took `[[docs]]` and left `(url)` as prose, in a note
   a path link to a `docs.md` that does not exist); a span the link rule refuses, `[[Note]](see also)`, and adjacent
   `[[A]][[B]]` stay wikilinks. A span that names neither a file nor a section, `[[ ]]`, `[[#]]`, `![[ ]]`, `[[a/]]`
   or `[[ | ]]`, stays literal as `[[]]` does (the review round 3: in a file document it rendered `<a href="">`,
   dressed as an external link that opened the page itself, or a path link to a nameless `a/.md`). Bash's `[[ -f x
   ]]`, Python's `[[1]]` and R's `lst[[1]]` in a reply are the dead span too, text preserved and the title accurate:
   no character rule separates them from Obsidian's valid targets (`[[ Note ]]`, `[[1]]`), and a per-kind grammar
   would be a ruling of the open ruling's kind. `![[image.png]]` renders an `<img>` when resolved, so
   rewriteFigureSrcs loads it from the file's folder and `![[image.png|300]]` sets its width; `![[Note]]` is a
   link-shaped chip `a.fv-embed`; unresolved, an embed is the dead span too (an `<img src="image.png">` in a reply
   would fetch from the page's own origin). An anchor's shown text is the source text at `textOffset` in the raw, so
   the anchor map places it exactly (a dead span is never mapped: a reply is not, and the URL kind keeps its place by
   blocks). The comments panel's embed grammar and the host's (`imageEmbeds` in file-comments.ts and
   tools/file-comments-host.mjs) read the `![[...]]` form: it was a one-regex addition, so the limit the design
   allowed for was not taken; file-comments-panel.test.ts and the host's tests hold both readers.
8. *rewriteFigureSrcs* reads every attribute a figure fetches through (figure-gate.ts figureRefs): an img's `src` and
   `srcset`, a `source`'s `src` and `srcset`, a video's `src` and `poster`, an audio's and a track's `src`, an svg
   `image`'s or `feImage`'s `href` and `xlink:href`. A srcset is rewritten candidate by candidate with its descriptors
   kept (HTML's own parse, a comma inside a URL kept). Only an img's `src` keeps `data-fv-src`, the one attribute the
   panel pairs an embed by. An `xlink:href` is folded into `href`: when both stand, `href` wins (SVG 2's rule) and the
   xlink attribute goes either way, so the element carries one attribute every reader agrees on. The URL kind resolves
   every one of those attributes against the document through the same walk (file-view.ts resolveFigureRefs, no
   `data-fv-src` since a URL document has no panel), where it resolved `img[src]` alone and the browser resolved a
   relative `srcset` candidate, a video's `src` or `poster`, an audio's, a `source`'s or a track's `src` against the
   page (the review round 2; md-config-url-figure-refs-browser.test.ts). file-view-figures-absolute.test.ts's selector
   pin is the gate's `FIGURE_SEL` now, with a case per shape. An `feImage` never reaches the rewrite or the gate
   today: the sanitizer's `svg` profile (md-sanitize.ts MD_PURIFY, no `svgFilters`) drops a filter's primitives first,
   so that arm is a guard for a wider profile, pinned over the stand-in together with the profile itself (a wider
   profile must bring a browser leg; the review round 1).
9. *Decision 8, the gate* (figure-gate.ts, run by mdBlock after rewriteFigureSrcs on the sanitized DOM). The allowed
   set is the gear's `figureHosts` (settings.ts `FIGURE_HOSTS_DEFAULT`: github.com, raw.githubusercontent.com,
   user-images.githubusercontent.com, camo.githubusercontent.com, avatars.githubusercontent.com,
   objects.githubusercontent.com, private-user-images.githubusercontent.com, github.githubassets.com, localhost,
   127.0.0.1; exact names, no wildcard) plus the page's own origin and the kernel's (`window.__rompKernelBase`), which
   every local figure goes through, plus the hosts clicked in this page (`loadedHosts`, a module Set that lives as
   long as the page, which is how Decision 8's "for the session" is built: the chat webview, the feed, the Files pane
   and each browser tab each remember their own, so a host clicked while reading one file is loaded for every file
   opened in that page afterwards, until the page reloads; the viewer's Reload or a Raw and back keeps a clicked host
   loaded, an emptied list gates a host the setting allowed; figure-gate.test.ts holds the set, and the gate leg
   re-opens the file and reads both clicked hosts loaded on open). An entry of the list is read down to its host name
   through the URL parser (settings.ts figureHostName, the reading remoteHost gives a source: an address pasted whole,
   a port or a path is stored as the host alone, an internationalised name in its `xn--` form, an IPv4 address without
   leading zeros; an entry with its own scheme is parsed as it stands, any other under `http://`), once per host; a
   line the parser refuses is kept as typed, allows nothing, and is named under the list in the gear (gear.js
   figureHostsNote). Before that a stored `https://cdn.test` or `cdn.test:8080` was a dead entry that gated the host
   it named, with no sign in the gear (the review round 1). A media root (img, video, audio, picture, svg; a `source`
   or `track` through its parent) with a source on another host is wrapped in
   `span.fv-gate[data-act="fv-load"][role=button][tabindex=0][data-fv-host]`, its label "Image from host. Click to
   load." (or Video, Audio), sized by the author's pixel `width` and `height` or the sheet's minimum box; every
   fetching attribute moves to `data-fv-gated-<name>` and `data-fv-src` to `data-fv-gated-fv-src`, so nothing leaves
   the page and no embed pairs while gated. The element stays inside the placeholder, which keeps the region layer's
   contract: with the panel open the layer wraps THE img inside the placeholder, and the click leaves the wrapper
   standing around the loaded picture (the leg reads both). The click is delegated on `.fileview-body` (and the URL
   viewer's body), never bound to the placeholder, since every paint rebuilds the DOM; Enter and Space on a focused
   placeholder do the same in both viewers (file-view.ts gateKeys: the URL viewer's `delegate` reads clicks alone, so
   its placeholder ignored the keys until the review round 1; md-config-url-gate-keys-browser.test.ts); the restore is
   the acknowledgement. One click restores every placeholder waiting on that host alone and relabels one waiting on
   more. The gear's list reaches an open document through the settings listener (regateFigures on `storage` and
   `romp:settings`): a host added restores its placeholders in place, a host removed applies at the file's next paint,
   which docs/reference.md says in those words (the review round 2). Nothing in the gate FINDS an element by class,
   since the sanitizer keeps an author's `class`: the placeholder by its `data-act`, its label by `data-fv-label`
   (LABEL_MARK), and the sheets' hide rule keys on the placeholder's `data-act` and the label's mark, neither of which
   the sanitizer lets an author write (round 3: keyed on the class it hid every child element, bold, a link or a code
   span, of an author's `<span class="fv-gate">` around prose; the box's chrome on the class stays, the recorded call;
   md-config-gate-author-span-browser.test.ts), so an author's `<text class="fv-gate-label">` inside a gated svg no
   longer takes the label's text and a `<span class="fv-gate">` around prose survives a click or a settings event with
   its text (the review round 1; md-config-figure-gate-authored-browser.test.ts). The srcset parse breaks on HTML's
   ASCII whitespace alone (a JS `\s` stopped at a no-break space, so `github.com<nbsp>@evil.test/x.png` read as
   github.com to the gate while the browser fetched evil.test) and leaves parentheses at the first `)` as HTML's
   descriptor tokenizer does, and every srcset under a judged root is written back in the gate's own spelling before
   the judgment, so the attribute the browser reads is the one the gate parsed. An inline svg's paint references are
   fetching attributes too (the review round 2: `fill`, `stroke`, `filter`, `clip-path`, `mask`, `marker-start`,
   `marker-mid` and `marker-end` take a CSS `url()`, DOMPurify's svg profile keeps all eight and its URI check passes
   `url(`, so a `url(https://host/p.svg#p)` on the svg or any element inside it fetched on open with no placeholder,
   in both kinds; figure-gate.ts paintRefs reads them with a CSS Syntax tokenizer, cssUrls, that preprocesses the
   value first as CSS Syntax's section 3.3 does (a CRLF pair, a lone CR or a FF is one newline: read raw,
   `\75&#13;&#10;rl(` had the escape eat the CR and the LF end the name, so the fill fetched on open with no
   placeholder; round 3), decodes escapes and skips comments, since `\75 rl(` is `url(` and `github.com\40 evil.test`
   is `github.com@evil.test` to the browser, judges every quoted string as well (a mask reads the CSS shorthand, so
   `image-set("https://host/a.png" 1x)` fetches), and moves the attribute to `data-fv-gated-<name>`; rewriteFigureSrcs
   leaves them as written; md-config-svg-paint-urls.test.ts and md-config-svg-paint-gate-browser.test.ts). The
   placeholder's text is skipped by the anchor map (isControl) and by the reader's place (reader-place.ts noteText),
   so an html block holding a gated figure at the top of the view keeps the place across a paint (its label had read
   against a parse of the block's source that reads nothing, and the Raw switch seated nothing;
   md-config-figure-gate-place.test.ts and its browser leg). The URL kind names the document's own host beside the
   list: the URL viewer fetches with `mode: "same-origin"`, so that HOSTNAME is the page's, but the gate compares
   origins (remoteHost), so a figure on the document's hostname under another scheme or port loads on open only
   through this arm (the gate leg's URL scene holds it: fx-alt, fx-port). The chat's `md()` is not gated (recorded).
   Measured on open, DPR 1, the fixture of file-view-figures-gate-browser: the one request that left the page was
   github.com's picture; `/file` served the file and its `![](fig.png)`; six placeholders held remote.test's img,
   srcset, poster, picture, svg and second img and one held other.test's. After the click on one remote.test
   placeholder: remote.test's img.png, img2.png, poster.png and svg.png were fetched and `/file` served local.png; the
   2x srcset candidate was not picked at DPR 1; for the `<picture>`, Chromium took the fallback img rather than the
   source's srcset when both came back on an element already in the document (the leg accepts either). A `<picture>`
   is gated whole, so its local fallback waits with the remote source. The gear's row is a textarea, one host per
   line; gear.js holds a copy of the default list, the host reading and the normaliser (it cannot import settings.ts),
   and gear-figure-hosts.test.ts holds them equal to settings.ts's. figure-gate.test.ts covers the pure parts (the
   srcset parse, remoteHost, the allowed set, the normaliser); settings.test.ts and md-config-figure-hosts.test.ts the
   field and its reading; docs/reference.md and the guide's Figures paragraph describe it.
10. *Not built here.* Obsidian's `%%comment%%` and `#tag` (the text names them for awareness only) stay literal.
   Slice 5's other items (refusal reasons for the remaining token names) are untouched; its goTo into a closed
   details is delivered here (item 5, the panel's revealMarks), since this slice is what makes a closed fold
   reachable from plain markdown. Open after the review round 2: a display formula under a highlight stays bare and
   a comment on one alone paints nothing in Rendered (an inline mark paints no wash over a block box; a block-level
   treatment, a class on the `.katex-display` element with a rule in both sheets, is a panel and CSS change;
   anchor-map-obsidian.test.ts pins the current shape); the chat's markdown fetches an svg paint reference on render
   as it fetches a chat `<img src>`, the gate being the viewer's (item 9); the callout body's trailing newlines are
   not trimmed as marked's blockquote trims its text (the pins hold the current output). Open after the review round
   3: block content inside a footnote definition (GitHub's four-space form: a fence, a list, a second paragraph) is
   not adopted and an indented fence renders as a code span (item 4; taking it needs the callout's nested block lex
   for the definition and the anchor map's walk over it, a plan change); marked's join of a paragraph and its
   interrupt-rejected successor renders one `<p>` when a display formula stands anywhere later in the note and two
   without (marked's own join, GitHub's rendering for those shapes; the map places both, item 2); a gated figure
   narrower than the placeholder's 14em minimum box gets a box of the minimum's width, so a 50px icon's placeholder
   is wider than the icon and the text below moves up by the difference after the click (the minimum is what lets
   the box name its host legibly; a box the figure's width wraps the label to a dozen lines and overflows, measured
   in round 3). Open after the review round 5: marked's blockquote and the callout differ on a lazy line indented
   four or more spaces that begins with `>` (item 5; marked's deviation from CommonMark, not copied); the person's
   bubble's code span keeps the 20% white wash it wore before the slice (white over it 3.35:1 dark, 3.51:1 light;
   item 1's washes are the slice's, that one is not), and the math fill's source fallback on that same wash, Slice
   1's 0.88 tint, reads at 2.95:1 and 3.09:1 (Slice 1's rule, recorded with it when the rule was chosen, the same
   standing; round 6); a formula wider than the paper prints cut at the paper's edge, and an inline formula with no
   break point (no top-level operator or relation) wider than the column overflows the column on screen with no
   scroll, the tail readable from Raw, where one with a top-level `+` or `=` wraps between its bases (item 1,
   KaTeX's nowrap, which no sheet rule scales; an inline-block scroll box of its own would lift every inline formula
   off the text's baseline, CSS 2.1 section 10.8.1, and make a breakable one a block, measured in round 6). Open
   after the review round 8: a hole's text is painted when it stands between two positioned characters of a range
   and not when it stands at the range's edge (paintRendered's skip of an endpoint that found no position and
   wrapBetween's wrap of everything between the two it has are main's path for tables and code blocks, which the
   slice's callout title and front matter inherit; the slice's one change on those lines passes the formulas), so a
   comment on a whole alert paints its body alone and one running past it paints the generated title too, text the
   source does not hold; painting a hole at the edge would paint tables and code blocks there as well, and never
   painting generated text would make the title a control, which changes mapRenderedSelection's refusal of an
   endpoint inside it (item 5; anchor-map-obsidian.test.ts's refusal test), so the rule for holes is Slice 5's, with
   its painter items. Open after the review round 9: the panel's unpaint (file-comments.ts unpaint, main's path,
   which the slice leaves as it is) normalizes a mark's parent once per mark, so unwrapping the marks of one
   paragraph costs the square of its inline children where the paint costs their count: 9,999 marks over a paragraph
   of 5,000 links painted in 33 ms and unwrapped in 469, 999 marks over 500 links in 3.6 and 5.5 (headless Chromium,
   the medians of five); normalizing each parent once after the loop unwraps the 9,999 in 11 ms, marks not laid out
   (md-config-paint-whitespace-browser.test.ts's timing leg does so on its own copy, so the paint alone is timed), a
   panel change for Slice 5's painter items. Open after the review round 10: the mapping's alphabet is JavaScript's
   `\s` on every side (anchor-map.ts Emitter.put drops each such character from a block's chars, nonWsBefore and
   nthNonWs count in the same alphabet, and the panel's quote matching, comments.ts normalize, collapses the same
   set), so a selection begun on a no-break or ideographic space, a full-width indent, is trimmed to the glyph after
   it: its highlight starts one glyph in (14 px at 14px sans-serif for U+3000) while the quote anchors; the trim is
   a pinned rule (anchor-map.test.ts, whitespace at the selection's edges), and a narrower alphabet is a change to
   the walk, the matching and the panel's normalize together, main's contract, for Slice 5's painter items. Open
   after the review round 11: a footnote definition's literal separator, the space md-config.ts emits between the
   back link and the body for the author's space after the colon that the marker's regex consumes (marked's task
   item puts one after its checkbox the same way), is a rendered space at the head of the body, so a highlight
   across the note paints it as a mark of its own beside the back link, which no mark holds, as it paints the task
   item's after its checkbox (a ruling, not a slip: the separator stays, since without it the note's copied and
   accessible text reads `1alpha` for `1 alpha`, an inline-block adding no separator of its own to a selection's
   text, and the sheets' margin-right alone halves the label's gap, 7.45 px to 3.86 at 15px;
   md-config-footnote-paint.test.ts and its browser leg pin the mark; a paint rule skipping a rendered space beside
   a control would skip the checkbox's too and reopen round 10's pin). Closed after the review round 12: round 11's
   wrap-point box (a collapsible space between two inline children at which the browser breaks the line, painted as
   the padding alone at the end of the line before the wrap, on main too) is fixed by the layout-time trim (item 2),
   which measures the mark in the browser's layout and unwraps it. Open after the review round 12, the trim's
   recorded shapes: (a) the fixpoint's price: a blank unwrapped as collapsed that renders once a later unwrap moves
   its line's wrap point back stays bare while the pane keeps the width: a mark is never re-wrapped (a blank at a
   line's last inch would flip with every pass), and the next paint pass at the same width paints the blank again and
   runs the same cascade over the same layout, so it unwraps the same marks in the same passes and leaves the same
   blanks bare (round 16; md-config-paint-trim-fixpoint-browser.test.ts leg 1 holds a second pass at each of its
   widths equal to the first in passes, blank marks kept and bare blanks), a ring gap of the space's width (3.89 px at
   14px sans-serif) at each such blank. In a fresh paint's trim at one width the shape followed the pass count in
   every cell round 16 measured: a trim that converged in two passes left none and one of three or more left some,
   from a few to about two thousand with the passage's length (the fixpoint leg's page under feed.css at 19 widths
   from 220 to 1,000 px: the 120-link item 4 at 220 px, 13 at 260 and 14 at 660, a paragraph of 600 links 27 to 207 at
   ten widths; the leg's own widths: the 5,000-link paragraph 2,005 bare at 700 px in eight passes, 1,884 at 400 in
   six and 2,095 at 300 in five, none at 800 and 500 in two; the 120-link item two passes and none at all five). A
   re-trim after a narrowing counts as well the blanks the old width's trim unwrapped that render at the new one
   (shape (b)), so its pass count bounds nothing: the leg's item narrowed from 800 to 700, 400 and 300 px converges in
   two passes and leaves 12, 10 and 12 bare (five passes and 44 at 500), the paragraph 648 to 3,267 (three passes at
   700 and 500, twelve at 400, eleven at 300). In the real Files pane (round 16, by content width): the 120-link item
   under one comment shows 24 of its 119 spaces bare at 420 px, 13 at 660 and 5 at 460, none at thirteen other widths
   sampled between 220 and 660; a paragraph of 600 links 167 at 220 px, 116 at 300, 83 at 380, 81 at 420 and 460, 71
   at 400 and 49 at 560, none at nine others; the panel's own pass at the pane's opening width, 460 px, leaves 5 and
   81, and a second pass at every width the same counts. The shape's size, measured in round 13 on the build box
   (headless Chromium, the trim leg's page under feed.css at 14px sans-serif, one comment across the passage; a bare
   blank is a whitespace-only text node below the top level with a Range width above zero and no mark ancestor, the
   browser legs' reading), is bimodal by width: none at most widths, and at a width where a line's slack falls inside
   the marks' side padding (4 px a mark; the Comments panel nests one mark per overlapping comment, so k comments over
   one passage put 4k px around every link and every blank of it, and the widths at which the flip happens move with
   the count: the nest figures below) the unwraps pull a word up onto line after line and the flip cascades through
   the lines below. The list item of fourteen links under one comment shows one bare blank of eleven rendered at 240
   px and four of ten at 220, none at the legs' six other widths; a list item of 120 links, sampled every 20 px from
   800 to 200, shows none at 25 of the 31 widths, 14 of 116 at 660, 1 at 640, 3 at 360, 13 of 94 at 260, 80 of 90 at
   240 (the 212 px content width takes two links a line untrimmed; the unwraps pull a third up on most lines, 50
   against 59, and the ring breaks at every space from the fifteenth link on) and 4 of 63 at 220, with 2 each at 550
   and 450 off that grid; a list item of 120 links of varied lengths 1 to 28 of 83 to 117 at 15 of the 31 widths; the
   paragraph of 5,000 links none at 800, 650, 600 and 500 px and 341 to 2,095 of 4,162 to 4,653 at 750, 700, 550, 450,
   400, 350 and 300 once the fixpoint completes (round 12's three-pass cap stopped short at five of these widths, with
   271 to 533 padding-only marks left and 1,111 to 2,095 bare). Overlapping comments (round 14, measured in the real
   Files pane, the panel leg's page under styles.css and files-pane.css, where the item's content box is the viewport
   less 66 px and the pane's 14.95px type makes a bare blank 4.75 px): the fourteen-link item under one to four
   comments at viewports from 200 to 420 px in 20 px steps shows bare blanks in 8 of the 48 cells and none in the
   other 40 (none at any count from 240 to 300 px, at 380 or at 400): under one comment 6 of 6 at 200 px and 1 of 11
   at 320 (under two to four comments at 200 px the item lays out one link a line and renders no blank); under two 2
   of 12 at 420; under three 8 of 8 at 220 and 4 of 10 at 320; under four 6 of 6 at 220, 4 of 10 at 340 and 1 of 11 at
   360. At 220 px under three or four comments every blank mark of the nest measures zero in the untrimmed layout (12
   or 16 px of padding around each link's 79.5 px of text in a 154 px content box puts every space at a wrap point,
   where under two comments 5 of the 13 are), so the pass's trim unwraps all 39 or 52 of them in one pass, the freed
   padding repacks the lines, and every one of the 8 (three comments) or 6 (four) blanks that then render stands bare:
   the highlight is a ringed box per link with a gap at every space, where under two comments at the same width 16
   blank marks stay and none is bare, and at 300 px the spaces are marked at every count. No padding-only mark stands
   in any of the 48 cells, so the property round 13 pinned holds where the ring's continuity does not;
   md-config-paint-trim-panel-browser.test.ts's nest leg runs at 300 px, a width where no blank flips at any count,
   and pins the padding-only count and not this shape's size, as every leg does. md-config-paint-trim-browser.test.ts
   bounds such blanks by the marks unwrapped and holds zero where nothing was unwrapped: a bound on the count, never a
   claim about its size. The layout-neutral mark, `.fc-hl` and `.fc-presel` with `margin: 0 -2px` beside their 2 px
   side padding in both sheets (a fileview-parity head), would keep the paint from moving any wrap point and remove
   the shape; it is a design call about main's comments feature for its owner, recorded and not applied. (b) A blank
   trimmed at one layout that renders at another stays unmarked until the next paint pass: the panel re-trims its
   standing marks on the seam's reflow, on a figure's load and on a font face's arrival (round 13's two triggers, item
   2), after a paint made in a hidden pane once the pane shows, and never re-wraps (the pending target's paint and
   unpaint, round 14's fifth trigger, are since round 15 a paint pass over the line boxes the target enters and
   leaves, closed since round 16 under the highlights standing in them, item 2: round 14's trim alone had left 2, 3, 4
   and 4 of the fourteen-link item's blanks bare after Cancel at 600 to 300 px and 4 and 2 while the composer stood at
   300 and 400 px, 2 and 1 with four links selected, where the leg now holds zero bare and zero padding-only, pending
   and after Cancel; md-config-paint-trim-panel-browser.test.ts bounds the rendered blanks left bare after its paint
   by the marks the trim unwrapped, shape (a)'s bound, and asserts nothing about them after a reflow; its pass unwraps
   something, an assertion of the leg, so the exact form, none where nothing was unwrapped, is
   md-config-paint-trim-browser.test.ts's, keyed on the event), so a blank trimmed before a
   figure or a face landed that renders after it is this shape under a new trigger. Its size, measured the same way:
   the 120-link item painted at 800 px (17 lines) and narrowed in one step shows 12 bare blanks of 113 rendered at
   700, 11 of 108 at 600, 44 of 110 at 500, 10 of 91 at 400 and 12 of 83 at 300, of which 9 to 12 are the blanks
   trimmed at 800 that render at the new width and the rest, 35 at 500, the re-trim's own unwraps pulling words up,
   shape (a) run during the re-trim; the varied list 12 to 19 of 104 to 116; the paragraph of 5,000 links (328 lines
   at 800) 295 to 3,267 of 4,110 to 4,627 once the re-trim's fixpoint completes (295 to 1,858 when round 12's cap
   stopped it short at 400 and 300 px); and a drag from 800 to 300 px in 10 px steps with a re-trim at each step (a
   window-edge resize's shape; the divider re-trims once, at release) leaves 115 of 118 rendered blanks bare on the
   120-link item and 95 of 97 on the varied one, since a blank that collapsed at any width on the way stays unwrapped:
   after a drag, nearly every space of an inline-heavy highlight is a ring gap until the next paint pass. (c) A form
   feed leading a block collapses as a bare text node (0 px) and renders as a 14 px glyph once it stands in an inline
   box of its own, a span or the mark alike (Chromium, both probed), so the trimmed paint keeps that mark and the
   highlighted paragraph shows the glyph where the unpainted one shows nothing
   (md-config-paint-rendered-space-browser.test.ts pins it; a form feed leading a block is written by no author). (d)
   A highlight from an html block into a markdown block after it is cut off and mislocated when the later block's
   whitespace-stripped text equals the html block's rendered text (a list item `**a**` after a block rendering `a`:
   the broken-img scene of anchor-map-fixtures/blank-scenes.json before round 13 re-lettered it, which had left that
   scene painting nothing past the html block) or when the sanitizer shortens the later block's source text (a
   stripped `<style>` in the list item, scene 86, whose letters differ from the html block's; round 13's probes over
   the real bundle, in which a plain `- b` after a block rendering `a b` pairs and `- <b>a</b> <i>b</i>` does not),
   the pairing defect Slice 5's list records (the resync across an html block, `runFits`); pre-existing on main and
   untouched by the slice. Scene 86 hits it, the union's one recorded case, so md-config-paint-trim-browser.test.ts
   confines its rendered-blank oracle to the top-level blocks the paint reached and holds that every other scene's
   paint reaches the closing paragraph (round 13 found two scenes passing every oracle vacuously: the broken-img scene
   above and a CRLF scene written with a lone CR, which marked reads as a blank line ending the html block;
   md-config-blank-scenes-fixture.test.ts pins the fixture's shape). Closed after the review round 13: the three-pass
   cap (the fixpoint runs to convergence, TRIM_PASSES_MAX a safety cap counted when reached; item 2); a nest of
   overlapping comments' marks peeled one level per pass (the trim measures each mark's text nodes); the pre-skip
   deciding a rendered blank under an author pre (a `pre` ancestor exempts the node and the trim measures it); a paint
   made while the pane was hidden left untrimmed on the show (the trim re-arms the panel's layout frame when the body
   has no box, which re-trims the show when the hide and the show fall in one task; a hide that outlasts a frame is
   re-trimmed by the seam's reflow report of the show, round 14's measurement); a figure's load or a font face's
   arrival re-wrapping the lines with no width report and leaving padding-only marks (the panel re-trims on both
   events); and a change whose every mark the pass's trim removed filed as shown (re-filed as not shown, its card
   offering Reveal). Closed after the review round 14: the pending target repainted alone over a highlight's lines (a
   composer opened or closed) leaving the highlight's wrap-point blanks as padding-only marks until a reflow or the
   next pass (the repaint trims the standing marks in the same call, item 2). Closed after the review round 15: that
   trim alone leaving the highlight's blanks trimmed at the old wrap points bare where they rendered at the new ones,
   while the composer stood and after Cancel (the repaint is a paint pass over the line boxes the target enters and
   leaves, item 2 and (b) above), and the same trim measuring every standing mark when a composer that paints no
   target opened or closed (a repaint that adds and removes no Rendered mark trims nothing). Closed after the review
   round 16: the repaint painting the highlights in the order of their first marks where the pass paints them in
   cards() order (two overlapping comments whose order by time was not their order in the text swapped nesting at
   every open and close and back at the next pass, a click on the overlap opening the other card meanwhile), the
   repaint reading the target's boxes alone (a highlight painted again whole in a box the target never touched landed
   inside the highlight or change mark standing there), and lineBoxOf stopping at an inline-block (the embed chip's,
   whose width follows its text, so a target on its text moved the paragraph's wrap points while no highlight of the
   paragraph was repainted; item 2). Closed after the review round 17: the repaint re-filing a change whose marks it
   painted again (one whose every mark the trim removed as not shown, one whose mark stands again as shown) and
   rendering no card, so the change card said the opposite of the body until the next render (a session's insertion of
   one soft hyphen, rendered at a line break alone; item 2). Pre-existing on main, found by round 16's review and fixed
   on 2026-09-10 (fork PR #712; until it, card-layout.ts and placeCards were byte-identical to 5917393e): the margin
   layout's pass was not a fixed point under a focus when two cards' marks shared a line, since card-layout.ts broke
   the tie on `desired` by the order the pass was given the cards in and placeCards feeds a non-render pass the DOM
   order it wrote in placement order, so when the tied pair straddled the focus's spill boundary each observer pass (a
   resize, a card's growth, a composer's open or Cancel) swapped the pair and moved the cards below by their height
   difference, and a render pass, the model's order, swapped them back. Of the two shapes named then (the pass fed the
   render's order, or an input-independent tie-break) the fix is the second: card-layout.ts breaks the tie by the
   cards' own fields in the list's order (a change card before a comment card, two changes by position then time, two
   comments by time, the key last), with card-layout tests that feed the placement order back under a focus; the
   margin-layout record in plans/file-review.md carries the rule. Recorded
   and not changed after rounds 13 to 16: the re-trim's price per reflow on the 5,000-link paragraph (item 2,
   re-measured under the convergence loop in round 14), the pending target's repaint on it (item 2, round 15's
   measurement), the change marks' whole-document repaint when one stands in a box (item 2, round 16's measurement)
   and shapes (a) to (d) above, (a) re-measured under overlapping comments in round 14 (its nest figures above) and at
   a standing width in the real pane in round 16 (its counts by content width above).

### Slice 5: comments anchor on real notes

Pair blocks inside an unclosed HTML container (a flattened walk); match code quotes raw; math tokens
as holes, no token names in refusals; report the first obstacle in document order (opening
`<details>` ancestors in goTo landed with Slice 4); overlapping `.fc-hl` keep one wash and a click
opens every card under it; paintAll hints with the last located start; strip cell delimiters from a
table quote; offer Comment on `selectionchange`. Acceptance: selections after the wrapper and details containers map;
the `total = a * b * 2` comment paints in Rendered; the math paragraph maps around the formula; a Raw comment across
two cells paints; a keyboard selection offers Comment. Tests: anchor-map and file-comments
fixtures. One more for the flattened walk, found in Slice 1's merge review (2026-09-08) and identical on main:
the resync across an html block (`runFits`, anchor-map.ts) accepts the first end from which the next block lines
up by whitespace-stripped text alone, so when a node the block rendered carries exactly the next paragraph's text
(a kept `<div>Go</div>`, or a `Go` hoisted out of a dropped `<form>`) the block takes no node, its own rendered
text maps to that paragraph's source offsets, and the blocks after it pair one node early: a later paragraph whose
text recurs maps to the wrong occurrence's offsets, the rest refuse. A tag test on a mapped block (`tagOf` already
names its element) closes the kept-element and hoisted-text shapes; an html `<p>` carrying the next paragraph's
text needs the run confirmed past it. Acceptance: the text-alike html node is refused and each paragraph after it
maps to its own offsets.

**The Slice 5 build** (2026-09-10). Branch `mdviewer-s5`, cut from the fork's main at 5bae9a67 (the merge of Slice 4,
fork PR #707) and moved to a3edbaaf7 before its first commit. After the build the branch merged the fork's main at
6aef10815 (2f79481b: 72 commits, fork PR #569's test-shim migration among them; two test files hand-resolved, named in
items 1b and 2), and 40a4db43a moved file-view-place-blocks.test.ts's node-list assertions onto the shim's sameNodes;
the review's round 1 landed as e5295ffa6, its round 2 as b1c6cb303 and its round 3 as 481b5f346; the branch then
merged the fork's main at 213fde5fa (50b19bfdb: fork PRs 740 and 741, the upstream folds, 746, and 747 and 748, the
file-review sidecar and tie-break slices; five files hand-resolved, item 9), and the review's round 4 landed as the
commit after the merge, each round's findings in the build report's round section. A probe over the real viewer
(2026-09-09, at 4def8dd8) recorded each defect before the build, and the ten rulings of 2026-09-09 on the points the
text above left open are cited below by number with what each said. The items take the numbers of the sentence above,
in the order it names them (the parenthesis on `<details>` is item 5; the reader's place inside a wrapper is item 1b
and the merge review's text-alike node item 1c), and a reference to an item below is to that numbering. The standing
rule for the build: these changes cause the file-comments feature no trouble, which item 10's last entry states as the
guarantees every test family re-verifies. Where the code as built departs from the text above, why, and which test
holds each rule:
1. *Item 1, the flattened walk: a linear tag scan and the nodes a wrapper nests.* An html block that leaves a
   `<div align="center">` or a `<details><summary>x</summary>` open is one top-level node holding the rest of the
   document in a browser, so its nested blocks' text occurred in no top-level node, the resync across it (`runFits`)
   fit at no end, the block took every node to the document's end and every later selection was refused as an HTML
   block at the wrapper's offset (the probe: four of four selections after a div refused; a `<details>` at offset 205
   took nine elements). Now `topTags` (anchor-map.ts, on the Walked row beside `tagOf`, left to right with no
   backtracking, as the comment scan is) reads an html token's raw once per source and answers the block's closed
   top-level tags in order and the chain it leaves open, with the parser's implied ends that decide the block's nodes:
   a `<p>` closes at a block-level start tag and at the raw's end (an open top-level `<p>` is no wrapper for a block
   whose first tag closes a `<p>`, which most blocks marked renders after it do, so a `<p align="center">` badge row
   keeps its one element; the blocks the parser DOES nest in it are read past since the review's round 3, `pOpen` and
   `nested`, below), a stray `</p>` is the parser's empty `<p>` (or, while such a `<p>` is open, the tag that closes
   it, round 3, below), void elements never open, comments and raw-text elements are skipped. The pairing
   (`analyzeRendered`) reads the scan first: a closed tag takes the next node when that node is its element (a
   `<style>` block whose element the sanitizer dropped takes none; `<p>Alpha</p>` over `<p>Beta</p>` take one each,
   where the map had paired them as nothing and both); an open tag takes its element and splices the element's
   children (elements, and text that is not blank) into the pairing right after it, so the blocks after the wrapper
   pair against the nodes the browser nested in it and the element is one of the block's wrappers; a wrapper inside a
   wrapper splices again, as two blocks or as `<div><div>` in one; the wrapper's own children in the raw (a summary)
   go to the html block through the resync as before, also when the block right after the wrapper is another html
   block (the review's round 1: the resync's run across an html block ends only where the next html block's first
   top-level tag finds its element at the candidate end, so a node the wrapper left over, its summary or its lead
   text, is read past to that element and the outer block keeps its summary; before, the run ended at any html block,
   the summary stayed in the content, the inner wrapper's scan found the summary where its element should be, took
   nothing and fell to every node to the document's end, so nested details, a details followed by a centred div or by
   an img, and a lead text followed by an inner div refused every later selection as an HTML block; an html block with
   no tag of its own, a comment or a closing tag alone, or whose element the sanitizer dropped, is read past as
   before; one edge left open at the time and closed in the review's round 3 by `TopTag.kids`, below: a leftover with
   the same tag as the next html block's first element, `<div><p>Lead</p>` then an html `<p>Alpha</p>`, ended the run
   at the leftover, the scan comparing tags alone); a block that is a closing tag alone (`</div>`, `</details>`, a
   stray `</span>`; `topTags` lists an end tag with no open element of its name as `stray`) owns no element, as a
   comment's does, and since the review's round 2 renders no node of its own either (`blank`, as a comment block is):
   it runs no resync and takes nothing, where before it ran one that, right before a paragraph carrying the OUTER
   wrapper's inline closer, confirmed at no end and, having no element, took every node to the document's end, so the
   closer and every later paragraph were refused as an HTML block at the closing tag's line; a block whose inline html
   closes a wrapper open around it (`**Bold** </div>`, `Last line.</details>`, a quoted `> line </div>`, a loose list
   item's line: any block since the review's round 2, not the paragraph alone) has its stray end tags read once per
   source (`blockEnds`, on the Walked row beside the tag scan, each with whether it stands inside a `<p>` the renderer
   emits, a paragraph's, a quoted paragraph's or a loose item's, and not a heading's or a tight item's), and a walk
   over the wrapper chain the SOURCE describes (the html blocks' open tags and stray end tags and the blocks' own
   closers, in order, as the parser keeps its stack) marks the block whose closer inside a `<p>` popped an open
   wrapper as `minted`: the parser closed the `<p>` with the wrapper and minted an empty `<p></p>` for the paragraph's
   own `</p>`, a node no block renders as, which the pairing steps over (the review's round 1: before, the next
   paragraph took the empty `<p>` as a mismatch, every later block paired one node early and the first rendered copy
   of a repeated paragraph mapped to the second copy's offsets; a stray `</div>` in a top-level paragraph mints
   nothing and nothing is skipped). The step is ONE model the pairing loop and the run check share (`pastMinted`; the
   review's round 2: the loop stepped over the minted `<p>` and `runFits` did not, and the loop keyed its step on the
   DOM's ancestry, so a wrapper with a leftover closed inline on its ONLY paragraph confirmed its run at no end, kept
   its element alone, and the closer was swallowed by the html block after it, an `<img>`, a centred div or a details,
   or every later paragraph paired one node early; and a `<form>` the sanitizer unwraps (KEEP_CONTENT, md-sanitize.ts)
   closed inline on a paragraph had no ancestor left for the DOM test and no element for the scan, so its block took
   every node to the document's end, where now the source's chain mints the `<p>` and the block is read past). Two
   more nodes the run check reads through since that round: an html block whose element the sanitizer unwrapped and
   whose text it hoisted (`<option>Opt.</option>` after a lead-text wrapper; `htmlText`, the block's text outside its
   tags and comments, on the Walked row) is read past with that bare text node, where before the text stood where the
   next paragraph's element was expected and the wrapper's run confirmed at no end; and the regions layer's span
   around a picture (`fc-imgwrap`, file-comments-regions.ts, present while the Comments panel is open) answers every
   tag test as its IMG (`tagNameOf`), so an html block whose first top-level tag is `<img>`, a standalone picture
   after a lead-text div or a details, a README's logo, finds its element with the panel open as without it (the
   review's round 2, HIGH: the span hid the IMG from `runFits` and from the scan's closed-tag take, so a wrapper with
   a leftover before such a block could not confirm its run, its nested passages were refused as an HTML block at the
   picture's offset and their comments did not paint with the panel open, while the same selections mapped with it
   closed; an `<img>` and a `<div align="center">` in one block took every node to the end). The review's round 3
   tightened the model in six places. `Block.minted` is set only for the end tags the parser honours through an open
   `<p>` (`P_CLOSERS`: the block-level elements plus button, center, dir, listing, select, li, dd, dt, applet, marquee
   and object; the end tag of a formatting element, `FORMATTING`, is the adoption agency's, so it pops the chain and
   mints nothing; any other end tag met inside an open `<p>`, `</label>`, `</span>`, `</option>`, is ignored by the
   parser and leaves the chain as it is: before, after a `<label>` closed inline the pairing skipped a following html
   `<p></p>` block's own element as the minted one and took the next paragraph's). `topTags` reports a top-level `<p>`
   the raw leaves open (`pOpen`) and the chain walk tracks it across blocks, marking `nested` the blocks the parser
   nests in it (an html block whose first tag is not p-closing, `<br>`, `<img>`, `<span class="w">`; a table, since a
   `<table>` start tag closes no `<p>` in DOMPurify's quirks-mode document; not a display formula, whose placeholder
   `<div class="md-math-display">` closes the `<p>` and is filled in place, so its span stands at the top level: the
   review's round 4, where round 3 had marked it nested, the open `<p>`'s block took the span and the formula's block
   owned nothing, the Raw offer at the formula lost), which the run check and the loop read past as blank, and turning
   a `</p>` block met while that `<p>` is open into a stray tag (it closes the p and mints nothing; before, every
   depth-0 `</p>` was the parser's empty `<p>`, and an image paragraph's `<p><img></p>` passed for it; `emptyP`, no
   element child, now decides in the run check and the scan's take as in the loop). `TopTag.kids` lists the nodes the
   raw itself puts inside an open top-level tag (each element closed directly under it, each run of non-blank text),
   which the pairing reads past after the splice (`pastKids`: a child the sanitizer drops with its text or a
   non-checkbox input passed over, an unwrapped one read as its text, the first the DOM does not hold as described
   ending the read), so the wrapper's own children are its block's without the resync and the next html block's scan
   starts at the first nested block (round 1's recorded edge closed: `<div align="center"><div>Lead</div>` then
   `<div class="in">`, and `<div><p>Lead</p>` then `<p>Alpha</p>` pairs the leftover to the wrapper). The run check
   reads a comment's mark over an unwrapped element's hoisted text as that text (`pastHoisted`, a run of text nodes
   and MARK elements whose text together is the block's `htext`; before, a comment spanning into a `<form>`'s lead
   unpaired every later block on the re-analysis). A block whose scan took nothing and whose run no end confirms hands
   the nodes back at the next html block's own element (`nextAnchor`, the blocks between passed over, `handedTo`), not
   at the document's end (a `<button>` opener whose paragraph's own `<button>` closes it now loses the paragraphs up
   to the next html block's element, or up to a block of closing tags alone (`</center>`), where the pairing resumes
   at the first end from which the blocks after it line up (`runFits`), main's per-block resync at such a block (the
   review's round 4: with a `</center>` alone as the only later html block the swallow had run to the document's end),
   and no more). And a selection's end boundary is placed by the last character it selects (`locate`, `descend`),
   never by the node that starts where it ends, so a whole-paragraph selection right before a bare hoisted text node,
   or a mark a comment painted over one, maps (main's rule and round 2's refused it as touching that block while a
   selection one character short mapped). Then the resync runs from there. Where no end lines up and the scan took an
   element, the scan's answer stands and the mismatch that follows is refused with its own node (the stripped-style
   scene of anchor-map-fixtures/blank-scenes.json, the Slice 4 note's item 10 (d): the list item whose source the
   sanitizer shortened is a mismatch with its own element and the paint reaches the closing paragraph); a block whose
   scan took nothing (a dropped `<style>` before a mismatched paragraph) takes every node up to the next html block's
   own element (`nextAnchor`, the review's round 3), where it took every node to the document's end before. Three
   consumers of the top-level assumption changed with it: a selection boundary descends from the top-level node to the
   deepest node holding it that a block renders as (`locate`), whitespace between nested blocks snapping to the nested
   block beside it and a boundary on a wrapper landing on its first or last nested block; `formulaExtra` reads the
   nearest node with a block, so a formula inside a nested paragraph names that paragraph's hole; and the cached
   index's shape (`shapeOf`) holds every wrapper's children, so the regions layer wrapping a picture inside a wrapper
   re-analyses as it does at the top level. One export for the reader's place (item 1b):
   `renderedBlockWrappers(renderedRoot, source, b): Element[]`, the elements of block b whose children the pairing
   took, in document order, empty for every other block; `renderedBlockIndex` answers for a nested node, and
   `renderedBlockElements` for a nested paragraph's block is its one `<p>`, for the wrapper's block the wrapper and
   what the resync left it (the summary). The wrapper's own block is never seated (ruling 2); since the review's round
   2 its Raw rows read as the first block nested in it (item 1b). Two consequences, accepted and pinned: a selection
   from the paragraph before a wrapper into a nested paragraph refuses as an HTML block, since the wrapper's block
   owns a node and is the first obstacle in the span (the probe had that selection mapping to a quote holding the
   `<div align="center">` line; a quote should not carry raw HTML the person did not select as text, and the Raw offer
   stands), and its mirror, a selection from a nested paragraph past `</div>`, maps with the closing tag's line inside
   the quote, as a comment block's does. The cost, as the build left it: a mark inside a document-wide wrapper read
   every highlight unit under the wrapper (`wrapBetween` and `unitsUnder` read the root's child holding the mark,
   which was the wrapper, so the scoped walk the Files pane freeze fixes brought was lost for such notes); the
   stand-in had said 2x (40 marks over a 1,000-paragraph note, 7.1 ms flat against 14.3 inside one `<div>`) and the
   browser disagreed (the review's round 1, headless Chromium: 0.78 ms a mark inside the div against 0.09 flat, 1.54
   at 2,000 paragraphs, 200 marks 178 ms against 21, a details 0.99), so the follow-up was built: `blockTopOf` answers
   the nearest node a block renders as (the pairing's table, idx.nodeBlock), the paragraph's own `<p>` for a mark
   nested in a wrapper, else the root's child, and `unitsUnder` takes such nodes at any depth (document order by
   `precedes`, the walk from the first to the last by `nextAfter`, a node holding the last entered child by child, so
   the rest of a wrapper after the passage is not read); both highlight paths read through it. After: 0.07 ms a mark
   inside the div against 0.09 flat, 0.22 against 0.14 at 2,000 paragraphs, 200 marks 14.7 ms against 21.1, and the
   real panel's repaint with 50 comments 28.5 ms inside a div against 29.7 flat (was 70.9). Not modelled by the scan
   and left to the resync: the parser's implied ends other than `<p>`'s (li, dt and dd, option; an unwrapped
   `<option>`'s hoisted text is read past, above), a top-level `<td>` or `<tr>` the parser drops (its text is read
   past as a bare node), a `<p>` left open INSIDE an open wrapper (depth one and more; the top-level case is modelled,
   `pOpen`), a start tag's implied end tags (a `<button>` closing an open button and the `<p>` around it: the swallow
   is bounded at the next html block's element, or a block of closing tags alone, instead, `nextAnchor`; the `<p>`'s
   button scope itself IS modelled since the review's round 4, `P_SCOPE_BARRIERS` in `walkedBlocks`: the blocks after
   a `<button>` block nested in an open `<p>` nest in the button until its closer, which leaves the `<p>` open, and
   the next paragraph closes it), and a formatting element a paragraph leaves open (a `<b>` with no closer), which the
   parser reconstructs as a top-level wrapper around every later block, so the next block takes the whole wrapper as a
   mismatch and every block after it has no node (pre-existing on main, byte-identical there; the fix shape, recorded
   in the build report's round 3: a `Block.leaves` of the formatting tags a paragraph leaves open, and after such a
   block pairs a following top-level element of that tag spliced and added to the block's `wrap`; routed to Slice 8's
   pairing work by the review's round 4, item 10 (j) and Slice 8's brief, section 2 (l)). The round 1 edge of the run
   check comparing by tag alone is closed (`TopTag.kids`, above). The review's round 4 tightened the model in seven
   more places. `CLOSES_P` is the parser's whole set for a `p` in button scope (center, dir, li, dd, dt, listing,
   plaintext and xmp joined it, and `P_CLOSERS` is that set plus button, select, applet, marquee and object; before,
   an html block opening a `<center>` after an open `<p>` was read as nesting in it and the paragraphs the browser
   nested in the `<center>` were refused where round 2 had mapped them, the fuzz seed 784's two map-backs). A stray
   end tag naming an element BELOW the open `<p>` in the chain closes the `<p>` with it, the parser's implied end tags
   before the pop, where one naming an element above it, a nested `<span>`'s or `<button>`'s closer, leaves it open
   (before, a `</div>` block after `<div>` and `<p>Lead` blocks left the `<p>` read as open and the `<img>` block
   after it nested, its picture swallowed by the `<p>`'s block, a regression against main). The `<p>`'s button scope
   (`P_SCOPE_BARRIERS`, above). `TopTag.kids` are recorded at every depth (`kidsAt`), and the depth-1 wrapper's scan
   sets k past the inner element after the splice and reads its own raw kids past (before, `<div class="in">` after
   `<div><div>` took the depth-1 wrapper itself and spliced its children a second time, a regression against main; the
   indented `<details><summary>` README shape among the five pinned). `pastKids` reads a `#text` kid as the run of
   text nodes and highlight marks from k, as `pastHoisted` does, two `#text` kids in a row as one run (an html comment
   splitting the text) and a `<mark>` the raw itself puts after the text as the next kid's (before, a Text node alone,
   so once a comment was painted on a wrapper's lead text the same-tag kid after it was taken by the next html block).
   A highlight `<mark>` whose every text node is blank, a control's included, is no node of the pairing's, at the root
   and in a wrapper's splice (`holdsContent`, `blankMark`: the panel paints its pass with the trim deferred, so a
   comment across a nested paragraph and an inline wrapper's opener left a blank mark between the `<p>` and the
   `<span>`, the span block's scan met it where its element was expected, took nothing, and every later block was
   swallowed until the pass's trim, a later comment across the same opener painting its first half alone; a
   formula-only comment's mark holds the formula element alone and stays the formula block's node). And `nextAnchor`'s
   bound at a block of closing tags alone (above). anchor-map-wrappers.test.ts (34 cases over
   anchor-map-fixtures/wrappers-plain.md, wrappers-2block.md and wrappers-unclosed.md, synthetic, and every scene of
   blank-scenes.json reaching its closing paragraph, the sanitizer's drops stood in for; four from the review's round
   1: the pairing across adjacent wrappers, the closing tag inside a paragraph, the formula at a selection's end, and
   the wrapper's per-mark cost as childNodes reads counted over 40 nested paragraphs; five from its round 2: a
   leftover wrapper closed inline on its only paragraph before an img, a centred div, a details or plain paragraphs,
   the regions layer's span read as its picture over a README's pictures and an `<img>` then `<div>` block, the
   unwrapped form and option, the closing-tag block right before an inline closer, and the closer inside a
   blockquote's paragraph or a loose list item with a tight item's and a heading's minting nothing; eight from its
   round 3, the stand-in's parser taught the ignored end tag and the button-scope close: `<label>`, `<legend>` and
   `<option>` closed inline before an html `<p></p>` block, a comment's mark over a `<form>`'s lead with every passage
   mapping after and a partial mark that splits the text, an open `<p>` followed by `<br>`, `<img>` and `<span>`
   blocks and by a table, the same-tag leftover in its div, span and `<div><p>Lead</p>` shapes, two closers and one
   closer after an open `<p>` and a README's centred `<p>` of a picture, the whole-paragraph selection by its text
   node's end and by its element's end before a hoisted text node, the summary, lead-text and banner comments counted
   once against the block's rendering, and the `<button>` opener's swallow bounded at the next html block; seven from
   its round 4, red over a git archive of 50b19bfdb: the display formula after an open `<p>` owning its span with the
   Raw offer at it, a comment painted on a wrapper's lead text with every passage after it mapping, a partial comment
   splitting the lead and an author's `<mark>` after it, the stray `</div>` and `</details>` closing an open `<p>`
   with the `<img>`, `<br>` and table blocks after them owning their elements, `<center>`, `<dir>`, `<li>`, `<dd>` and
   `<dt>` wrappers after an open `<p>` with the `<button>` control's nested paragraphs refused as the `<p>`'s HTML
   block, the depth-1 wrapper before a same-tag block in five shapes, two comments across an inline wrapper's opener
   painted with the trim deferred, and the `<button>` opener bounded at a `</center>` alone; and test 27 given the two
   selections that distinguish the trees, the whole paragraph ending at the hoisted text node's offset 0 and at the
   root's child index, red over b1c6cb303 where round 3's pin had passed) and anchor-map-wrappers-browser.test.ts (6
   legs over the real viewer and the real panel, real-viewer-leg.ts: the Files pane at 900 and 380 px, the two-block
   fixture, the chat modal, and, the review's round 2, the panel OPEN over a standalone `<img>` block after a
   lead-text div and after a details, a README's logo, screenshot and demo pictures, an `<img>` then `<div>` block and
   the seeded lead-text div closed inline on its only paragraph then an img, every nested passage mapping and the
   comment served on it painting with a Scroll link; and, its round 3, comments served on a details summary, a
   two-line summary, a centred div's lead text and a README banner's tagline and heading painting with marks and
   Scroll, a comment spanning from the paragraph before a `<tr><td>` note into its nested paragraph with the five
   passages mapping after, the open `<p>` with `<br>`, `<img>` and `<span>` blocks and with a table, the same-tag
   leftover, the stray `</p>` after an open `<p>`, and the `<button>` opener with the paragraphs inside its run
   refused at the button's block and every passage after the next html block mapping; each drag maps to the passage's
   offsets, offers the float and opens the composer with the quote and Save; the anchor-map exports ride a probe
   bundle injected after the load, so its cache is not the panel's, and the panel's own mapping is read through the
   composer's quote). md-config-paint-trim-browser.test.ts's confinement of its rendered-blank oracle to the blocks
   the paint reached is lifted: every scene reaches its closing paragraph, and the fixture's note says so.
2. *Item 1b, the reader's place inside a wrapper* (ruling 1: build the descent in this slice, since the pairing alone
   made the Raw to Rendered direction seat a nested paragraph while Rendered to Raw still read no place). readPlace's
   Rendered read (reader-place.ts `readRendered`) is one level of element children at a time: topVisibleIndex over the
   level's boxes, then, for the child the search lands on, its block's wrappers; a child that is one of them stands
   for the blocks nested in it and its element children are read in its place the same way, recursively; a child
   paired to a wrapper's block that is not itself a wrapper (a `<summary>`; a `<p>Alpha</p>` the same block closed
   before opening the `<div>`) is a row of the block's own and is passed over for the block after it, never the place,
   so the wrapper's box at the edge reads the first nested block and a closed `<details>`, whose content the browser
   does not show, reads the block after it (reader-place.ts `boxOf` asks checkVisibility where the browser has it, the
   rect-zero rule standing first and a browser or stand-in without the API reading the rect alone: Chromium lays a
   shut fold's content out all the same, the first hidden paragraph's rect coinciding with the block after the fold's,
   so the rect alone had read the hidden paragraph as the place and the Raw switch seated the fold's hidden source at
   the edge under the summary's row where the reader had the block after the fold in view; the review's round 1); a
   level holding nothing at or below the edge hands back to its parent's. Per level rather than over one flattened
   list: the map's index checks the root's shape child by child on every read and readPlace runs on every scroll frame
   (file-view.ts notePlace), so a read per top-level child would cost the square of the document. The two differ in
   one shape, not pinned: a floated figure inside a wrapper whose box reaches below the wrapper's bottom while the
   edge is past that bottom beside the figure reads the next top-level element here where the flat list would pass to
   the figure's neighbour. Beyond what was first designed, which named the summary alone: every element paired to a
   wrapper's block that is not a wrapper is passed over, the closed-before-open `<p>Alpha</p>` included, where it was
   refused before (the numeric scrollTop stood); the same rule as ruling 2's, a stale scrollTop being worse than the
   first nested block. The seat still never seats the wrapper's own block (ruling 2: ownedElements' DOMParser check
   refuses it), but since the review's round 2 the Raw read reads every row of that block (the opener, the
   `<summary>`, a README's `<h1>` and `<p>` lead rows, an `<img>` line, and the blank row before the opener) as the
   first block nested in it, the owner's ruling extending the closing-row rule to the opener rows (reader-place.ts
   `readsAsNext` and `nextShown`; whether a block opens a wrapper is told by the browser's own parser, `opensWrapper`:
   the block's source with a `<p>` appended, as marked renders the block after it, parsed by DOMParser, and the
   paragraph read back nested inside an element of the block's, so an open `<p>` is closed and an unclosed `<table>`
   foster-parents as the browser does; a lex and a parse of the block per scroll frame while such a row is on top,
   item 11's costs), through a run of such blocks, so a Raw row of `<summary>` or `<div align="center">` switched to
   Rendered seats the first nested block where its own row was and a fold title at the pane's top round-trips exactly
   at 900 and 380 px (before: 26 and 203 px lost for an open fold); the same rule reads a block of closing tags alone,
   one or several (`</details>\n</div>`, `</details></div>`: `closesAlone`; before, a two-closer block was its own
   place and seated the last nested paragraph at the row, the block after it 21 to 110 px low) and a comment block
   (`isCommentBlock`, over the pairing's own `commentsOnly`, exported from anchor-map.ts so the two agree; before, its
   own place, seated through the block before it, 71 px off, or refused right after an opener) as the block after them
   (the review's round 1 had read a closing tag alone so: with the read fixed alone the shut fold's Rendered to Raw
   and back lost 370 px at 900 px and 553 at 380, the closing row on top of Raw, its block owning no element and its
   seat walking back through the fold's unshown paragraphs to the wrapper's refused block, so the numeric scrollTop
   stood, off by the fold's source height; the round trip is exact now, 0.0 px at both widths, from a summary at or
   above the edge; from one below it the cap costs the summary's depth, below); a nested paragraph's row seats at its
   own `<p>`; a block of the document's last that renders nothing stays its own place and seats the last nested
   paragraph through the nearest-before fallback. A Raw row inside a `<details>` shows its text whatever the Rendered
   view's fold state, and that state is the DOM's alone (file-view.ts's fold keeper restores a fold as the person left
   it, before the seat), so the place read there keeps its own block and CARRIES the block after the fold, and after
   each fold in turn that block lies in, each with its first row's top (`Place.after`, from a per-source table of
   `<details>` depths, `foldDepths`, fences and comments skipped; `foldStands`); the seat stands on the first carried
   block the view shows when the kept block is not (the review's round 2, HIGH: a shut fold whose summary wraps had
   put the fold's hidden rows on top of Raw after the switch, the way back refused them, and the reader landed 361 px
   down at 900 and 562 at 380), and no lower than the fold's summary at the edge (the review's round 3, the owner's
   ruling: the seat stands on what is shown; `shownFoldOf`; seated at its own row's top alone, the carried block after
   a fifteen-paragraph fold put the summary 816 px down at 900 and 1713 at 380, off the pane, from the fold's own
   rows, a hidden row inside it, or the `</div>` of a wrapper closed right before it); the same cap holds a block read
   through a shut fold's closing row and the rows after it that render nothing (`shutFoldBefore`: the fold's summary,
   or a shut fold ending a wrapper before the block; round 3, HIGH: seated where its row was, 54 to 90 px down, the
   block after the fold left the block before the fold's tail 13 to 35 px under the edge, the way back read that tail
   by its fraction, and the fold's whole source came back between, 427 to 463 px at 900 and 787 to 823 at 380; now the
   way back loses the Raw rows' excess over the summary's box alone, 24 to 60 px, the recorded class; the cap costs
   the plain closing row AT the edge 6 px on its round trip, exact before, its block's row 36 px down against the
   summary's 30, and a shut fold's summary 2 to about 8 px below the edge in Rendered, the paragraph before the fold
   out of view, its depth on the Rendered to Raw to Rendered trip, the summary pulled to 0.2 px (2 and 5 px measured
   at 900 and 380; the band is the summary's margin over the block before the fold; the review's round 4's record),
   where the summary at or above the edge is exact; a carried block whose row's distance leaves the summary partway
   above the edge keeps it, so the round trip from a wrapped summary 10 px in stays exact where a seat AT the edge
   from any hidden row would lose the 10 px (the cap, not a seat at the edge from every hidden row, is the rule,
   accepted by the review's round 4; the closed-details node test 4 and browser tests 4, 7 and 8 pin it); and the
   round trip from the fold's OWN rows, the opener, the summary, the blank after it, still loses the fold's source
   height, 402 to 420 px at 900 and 744 to 780 at 380, round 2's 406 to 413 and 683 to 690 with the landing now right,
   since the way back from the summary at the edge is ruling 13's, the block after the fold at its distance with the
   fold's source above), and a fold the person opened seats the row's own paragraph as before (the review's round 4:
   round 3's `shutFoldBefore` had read an OPEN fold's summary, met as the previous shown sibling of the fold's first
   nested block, as a shut fold's, so from the fold's own Raw rows the first nested block was capped at the summary,
   the `<summary>` row's round trip lost 6 px where it had been exact, paragraph 11 at 30 px against its 36, and the
   opener's row put the summary at the edge in place of the row's own distance; a summary whose fold is open caps
   nothing now, paragraph 11 back at 36 with the summary at 6.2, the opener row landing it at 54 and returning 31 px
   low, the recorded open-fold class, and the shut fold's summary a stand-in reading rects alone reaches is capped as
   before; the closed-details node test 6 and browser test 9 pin it); a paragraph inside a shut fold whose place
   carries no block after the fold (a place of another making) still seats nothing. file-view-place-blocks.test.ts
   (14; the two wrapper tests rewritten, the stand-in's wrapper children given boxes stacked inside the wrapper; built
   with the stand-in on the shim ratchet's allowlist, unswitched, then switched by the merge of main 6aef10815, which
   brought fork PR #569: FakeNode, FakeText and FakeElement end their constructors in hideEdges, main's projection
   case is the fourteenth, the ratchet's allowlist is empty with ALLOWLIST_MAX at 0, and 40a4db43a asserts the file's
   non-empty node lists through sameNodes, by identity; the merge's hand resolve kept the rewritten test 10 with
   main's one sameNodes assertion carried onto its equivalent line), file-view-place-html-browser.test.ts (10; tests 3
   and 4 exact round trips as before: the picture after a `<details>` back at its depth within the Raw row's
   whole-pixel snap scaled by the picture's height over the row's, about 5 px at 900 px; the rule scene moved 2 px
   below the edge, since `.fileview-md hr` is a 1 px hairline whose bottom at 0 sits on the very bound topVisibleIndex
   reads and the browser's sub-pixel snap then decides which block is the place; test 3's summary row switched to
   Rendered puts the fold's summary at the edge (round 3; round 2: the block after the shut fold where its row was,
   100 px down); and from the review's round 2 a fold title at the top edge, open and shut, at 900 and 380 px, exact,
   with the closing row followed by a comment, and a README's centred header from Rendered and from each of the
   wrapper's rows; and, its round 3, the wrapper's own picture, a logo and a 900x600 banner, at 900 and 380: from the
   picture's top to 300 px in, the picture back within the row's whole-pixel snap scaled by the picture's height over
   the row's, test 3's bound (4.5 px for the banner at 900, under 2 px for the other three; the review's round 4
   measured 3 px for the banner 300 px in at 900 and 0 to 1 px in every other scene), and from its Raw tag row at the
   edge and 9 px above it, the picture at the row's fraction within the same bound, 0.5 px measured, and the row back
   within 1.5 px; and, its round 4, test 10: from the `<div align="center">` opener row and the blank before it, the
   logo and the banner at 900 and 380, the picture at its row's distance below the edge and the row back in view; test
   8's `<img src=` row scene at both widths), file-view-place-wrapper-end-browser.test.ts (3; tests 1 and 2 exact:
   nested paragraph 60 in a centred div closed last, never closed and `<details open>` closed at the end lands on its
   own Raw row and returns within 1.5 px, and its Raw row 3 px above the edge seats its own `<p>` at the row's depth
   scaled), file-view-place-edits-browser.test.ts (4; test 1 tightened to exact, paragraph 80's own row and back at
   the same height), file-view-place-closed-details.test.ts (9, the review's rounds 1 to 4: a stand-in whose elements
   answer checkVisibility as Chromium does and one without the API; the read; the seat's refusal for a place carrying
   no block after the fold; the Raw read of closers, comments, the wrapper's rows and the carried blocks, a chain of
   two folds included; the seat standing on a carried block, capped at the summary since round 3; and, round 3, the
   wrapper's own picture read and seated at its fraction; and, round 4, an open fold's summary capping nothing where a
   stand-in's shut fold's summary still caps, the Raw read carrying the picture from a row before its tag row, the
   Rendered read carrying a picture below a lead `<h1>` the edge is inside, and the Raw row at the edge kept across a
   reflow) and file-view-place-closed-details-browser.test.ts (10 legs over the real viewer: the round trip at 900 and
   380 px; the closing row from Raw for a shut and an open fold; the hidden row seating the block after the fold and
   the opened fold seating its own paragraph; the wrapped summary's exact round trip at both widths; the two-closer
   block from either row; comment rows inside a wrapper; and, the review's round 3, the long fold's rows and the
   sibling `</div>` rows at 900 and 380 with the summary at the edge, and the closing-row round trips with a comment,
   a reference definition, the blanks beside the closer and the wrapper's `</div>`; and, its round 4, the open fold's
   `<summary>` row round-tripping exactly with the first nested block at its own distance, and eight Raw rows held
   within 0.4 px across A+, A- and a pane drag at 900 and 380). The edge inside a wrapper's own lead picture (a
   README's banner or logo in a centred div, a linked logo, a badge row), or a row of the block's own at the edge with
   the picture below it, is the one row of a wrapper's block the seat stands on in both directions (the review's round
   3, widened in its round 4; `Place.pic`, the picture's tag line and its box: readRendered carries the first picture
   of the block's own rows, from the level's first box on, that ends below the edge, the picture the edge is inside or
   one below the edge under a lead `<h1>` the edge is inside, the walk ending at the first nested block or wrapper;
   readPlace's Raw branch carries the first `<img` line at or after the top row of a block that opens a wrapper, the
   tag row itself, the `<div align="center">` opener, an `<h1>` lead row or the blank before the opener, with that
   line's own row (asking `opensWrapper` of that block a second time, a lex and a parse more per scroll frame while
   the row is on top, item 11's costs); and the seat puts the picture, or the row, at the same fraction of its height
   when the edge is inside it, the rule a top-level picture has had since Slice 2 and the html leg's test 3 pins, and
   at the same distance below the edge otherwise, as any block that starts below the edge keeps its own; the picture
   is found from the tag's index among the block's `<img` tags, `picturesOf`, `imgLine`, `imgIndexBefore`, `picBox`,
   and a picture the view does not show leaves the seat to the rules below). Round 4's correction (HIGH, against main:
   a wrapper's own row BEFORE its lead picture's tag row read as the first nested block at its row's distance, so the
   switch to Rendered put that block there and the picture, 120 to 508 px tall against one Raw row, above the edge,
   the logo's top at -40.5 and the banner's at -428.5 at 900, and the way back seated the tag row at the picture's
   fraction, the opener's row 32 to 109 px above the edge and off the pane, where main had kept it in view 38 to 45 px
   low): from the opener row and the blank before it the picture lands at its row's distance, 18 and 36 px, and the
   row returns in view 23 to 27 px low at 900 and 380 (the paragraph before the wrapper's tail by its fraction, the
   recorded class); the `<h1>`-and-banner README's opener, blank and `<h1>` rows round-trip exactly (65 to 109 px off
   before); the picture's top 2 px below the edge round-trips exactly (59 to 447 px off before); and the `<h1>` 10 px
   in puts the tag row in Raw where the picture was and returns 26 px low (before, the write was clamped at the
   document's top). The closed-details node tests 7 and 8 and the html leg's test 10 pin it. The owner's round-3
   ruling asked for the picture's top at the edge both ways, the same rule at the top level; the fraction was kept
   instead, since the top level's fraction round-trips exactly and the header states it, and the picture's top alone
   would lose the reader's depth (150 to 300 px into a banner) and regress the from-Raw scenes with the tag row
   partway above the edge; the review's round 4 accepted the fraction as the rule, pinned by the html leg's test 9 and
   the closed-details node test 5. Before: read as the first nested block below the picture, whose row the Raw seat
   put where the block was, the paragraph before the wrapper topped the Raw view whenever the picture's height above
   the edge exceeded the wrapper's rows and the way back was its fraction seat, 36 px for a logo's top at the edge at
   900, 430 to 442 for a banner 50 to 300 px in, 70 to 82 for the banner at 380, and 40 in reverse from a data: URI
   row wrapping to 144 px at 380 (html leg tests 8 and 9, closed-details node test 5). And the way back from rows that
   render nothing on top of Raw (a closing-tag row after an OPEN fold, a reference definition, a comment, a
   `<div align="center">` opener row) loses their Raw height's excess over the Rendered box between the previous
   block's tail and the block after them, by that tail's fraction seat: 38 to 78 px for an open fold's closer, 41 to
   43 from a `<div align="center">` opener row, 96 to 121 after a display formula inside a wrapper (three Raw rows,
   one 18 px line rendered), 78 to 96 from the opener row of a shut fold whose text sits in its html block, 60 to 78
   from its summary row, 42 to 60 from its text row (900 to 380), against 9 for a plain blank row: the fraction seat
   of the partway block is the design's rule, and the residual grows with the rows. A text-size step with a fold's
   summary at the top edge in RENDERED moves the title 4.5 to 4.9 px above the edge per step, compounding (-4.7, -9.3,
   -15.3 over three steps at 900): the kept block, the block after a shut fold or the first nested one, keeps its
   distance and the summary's own growth lands above the edge. Recorded: the fix shape is the picture's mechanism
   widened to every shown row of a wrapper's block for a same-view reflow, which touches rulings 2 and 13, so it is
   the owner's call and not built (the review's round 4 found no one-line fix either: the summary is passed over and
   the place has no field for it). In RAW the rows hold since the review's round 4: a reflow of the same Raw text (a
   text-size step, the pane dragged, the Comments aside opening or closing) keeps the top ROW (`Place.row`, the row at
   the edge when the kept block starts at or below it, its span and its top, set by readPlace's Raw branch;
   seatPlaceOutcome, for a seat in Raw over the same source, puts that row back where it was, before every other
   rule), so the `<summary>` row, a comment's, a closer's, a wrapper's opener, the blank before a fold's opener, the
   blank after a closer, a blank between paragraphs, a reference definition's row and a logo README's opener hold
   within 0.4 px across A+, A- and a pane drag at 900 and 380 (before, a row read as the block after it rose 2.7 px
   for each row between them, 5 to 11 px per step, where main, which read each such row as its own block, held them
   within half a pixel: the `<summary>` row 4.9 to 5.4, the blank before a shut fold's opener 10.8, the logo README's
   opener 15.9 at 900 and 47.1 at 380; a plain blank row rose 3 px on main and here alike, and holds now); a
   paragraph's own row is unchanged (`Place.line`). The closed-details node test 9 and browser test 10 pin it. The
   Slice 2 note above records refusals (1) and (2) as history now.
3. *Item 1c, the text-alike html node* (ruling 10: the tag test with the two-block confirmation, the last-block
   exception stated). `fits` requires a mapped block's element tag as well as its text when the block has text
   (`tagOf` names P, H1 to H6, UL, OL, BLOCKQUOTE, PRE, TABLE, HR, DETAILS, DIV); the empty-text branch stays
   text-only, since an image paragraph wrapped by the regions layer's span pairs by empty text. `runFits` confirms a
   run by TWO mapped blocks with text where two exist, so an html `<p>Go</p>` before the paragraph `Go` fits the first
   and not the second and is not taken for it; the same-text list item (`- **a**` after a block rendering `a`, the
   other trigger of the Slice 4 note's item 10 (d)) is closed by the tag test alone, a UL never fitting a P. The
   last-block exception as it now stands: a closed tag the scan can see (`<p>Go</p>`) is taken before the resync, so
   the exception needs a dropped wrapper, and a `Go` hoisted out of a dropped `<form>` before the note's FINAL
   paragraph `Go` is taken for that paragraph (the quote is still the paragraph's own source; the leftover `<p>` is no
   block's), pinned as it stands. The tag test can turn a wrong pairing into a mismatch refusal and never the reverse
   (md-sanitize-anchor-map-browser.test.ts's mismatch refusals stand). anchor-map-wrappers.test.ts.
4. *Items 2 and 8, code quotes raw and table quotes with their pipes as blanks, at paint time* (ruling 5: the plan's
   "strip cell delimiters from a table quote" is read as a PAINT-time rule; the stored quote stays the exact source
   slice, which the host's byte-exact locate requires, renderComposer is untouched, and the browser leg pins the
   posted anchors). paintRendered's fallback matched a quote stripped of inline markup against the rendered text, the
   strip that serves prose: the emphasis rule took the asterisks out of `total = a * b * 2` and the needle occurred
   nowhere (the comment painted in Raw alone, its card offering Reveal and no Scroll link), the heading rule took the
   `# ` off `# a comment` so it painted two characters in, and a Raw comment across two cells kept its pipe in the
   needle against cells with nothing between them. The build and the review's rounds 1 and 2 read the scope line by
   line by hole kind through a hand-written inline strip (`scopeMapped` over regex rules for the emphasis pairs, the
   escapes, links, tags and the hard break, code spans and escapes masked, a row cut into cells by backslash parity),
   each round's rules in the build report; round 2's rework of the emphasis pass regressed a class of cell and prose
   shapes (a lone delimiter inside an emphasis pair, `_snake_case_`, `**5 * 3 = 15**`, `~~a ~ b~~`; an intraword
   underscore, `_a_b_`, `___a___`; an escape or a backslash before a tag inside an html block; a literal angle
   bracket, `Edit <path/to/file> first`; an undefined footnote reference), and the review's round 3 retired the strip.
   The fallback now reads the scope through the markdown pipeline itself (`renderedBlocks`): marked's tokens for the
   whole document (the one configuration's lex, cached on the source's table, so the document's link definitions and
   footnote book decide whether a reference link, a reference image or a footnote reference is a construct or literal
   text, as the rendering decides), each token's shown text written out with a source position per character
   (`TextEmitter`; `lenientBlocks` and `lenientInline` mirror the exact walk's placement, walkBlocks and walkInline,
   and never refuse: an entity is decoded, a label marked rewrote is aligned by its shown text), and what the DOM does
   to marked's HTML applied as text rules where no DOM is to hand (the parser decodes entities; the sanitizer removes
   `<script>`, `<style>`, `<iframe>`, `<noscript>`, `<template>`, MathML, `<noembed>`, `<noframes>`, `<xmp>`,
   `<plaintext>` and svg's `<foreignObject>` (the review's round 4) with their text, `DROPPED_CONTENT`, and unwraps
   every other forbidden element keeping its text). An html block's text is the text between its tags as written,
   entities decoded and the dropped elements' content left out (`lenientHtml`: marked passes an html block through, so
   `costs \$5` in a `<div>` is the two characters it shows and a backslash before a tag stays); a code block's lines
   are the code as written, the fence lines dropped since they render nothing (line i of the token's text is the tail
   of the raw line holding it, past the opening fence, so a quote begun inside the info string or over the whole block
   still paints from its first code character); a table is read cell by cell as marked's splitCells cuts a row
   (`lenientRow`: a blank at each delimiter's position, `\|` the cell's pipe, a blank first or last cell dropped,
   cells past the header's count dropped), the delimiter row kept as its dashes, which no rendered text holds, so a
   quote spanning it still paints nothing and the card keeps Reveal (item 8's rule, kept); a picture, a hard break and
   an inline formula show no text (the formula's glyphs are a control the hay skips); a footnote reference shows its
   ordinal; a wikilink its file-document text. The quote is the rendered scope's characters whose origin lies in the
   range (`mappedSlice`), never a rendering of the raw slice on its own: a quote cut inside an emphasis pair
   (`bold words** more`), begun mid-line after a lead-like `2024. ` or `# `, or spanning a construct wrapped across a
   soft break (`**an important` at one line's end and `phrase**` at the next's start) reads as the rendering shows
   those characters, the block having been read whole; a paragraph continuation line beginning `3. ` or `10) `, text
   to marked, keeps it; a hard break shows nothing on both sides (round 2's needle kept a line feed the hay never
   held, so a quote across a hard break in a refused paragraph never painted). Needle and scope are one text, so the
   ordinal count guard stays exact: a repeated code line or a repeated row paints the range's own by ordinal, a quote
   across two body rows paints both cells, and the hay puts a blank between two adjacent table parts (`hayRuns`;
   `codeRuns` unchanged), which fires only in a DOM without whitespace nodes between the cells (Chromium's table DOM
   carries them). Test 10 of the file stands as the control for a list item's prose read as its rendering and its code
   hole raw (a code token the prose repeats inside a link's label and URL counts alike on both sides). The fallback's
   scope is the range's blocks' nodes less their wrappers (`idx.wrappers`; the review's round 3, HIGH: a wrapper's
   text holds every block nested in it and the leftover the block owns beside it, a summary, a lead text, a banner's
   heading, so the hay had counted a comment on the leftover twice against the block's rendering once and refused it,
   where main painted it), and, since the review's round 2, the whole rendered text when that scope's text holds no
   occurrence of the quote (HIGH: on main a block inside a swallowed wrapper had no node, the scope was empty and the
   whole text was searched, so its comment painted; the slice's pairing gave such a block a WRONG node when a cascade
   started, the wrapper's leftover, the minted `<p>` or the previous paragraph, marked a mismatch, and the scoped hay
   held no occurrence, so every residual pairing error also unpainted a comment main had shown, 201 of 2,000 in the
   finder's census) or, since round 3, a different number of times than the blocks' rendering holds it (a wrong node
   whose text held the quote a different number of times still refused), the whole text's counts then having to agree.
   Read by rule rather than from the DOM, for the record: the sanitizer's drops (no DOM in the node tests); a
   wikilink's shown text is the file document's (the chat's unresolved span shows the source); a named character
   reference outside `NAMED_ENTITIES` keeps its source form (since the review's round 4 the table is HTML 4.01's 252
   names with HTML5's code points, `apos` and the upper-case aliases `AMP`, `COPY`, `GT`, `LT`, `QUOT` and `REG`, so
   an HTML5-only name such as `&check;` is what stays; round 3's table held six names, so `&mdash;`, `&copy;` and
   `&hellip;` in a README's html blocks and cells never matched the glyph the DOM shows and a comment on such a
   passage painted nothing; in an html block, whose raw marked passes through, the 106 legacy names and a numeric
   reference decode with no semicolon as the parser decodes them, `charRefAt` and `decodeHtmlText`, an unknown name
   taking its longest legacy prefix, `&notit;` the not sign and `it;`, while in a paragraph marked's escape keeps a
   semicolon-less reference literal; a numeric reference follows the parser's end state, `numericRefText`: U+FFFD for
   zero, a surrogate and a code past U+10FFFF, the windows-1252 character for a C1 control, and one map entry per code
   unit, so an astral character's quote keeps its last character); a `<pre>` inside an html block keeps the newline
   after its start tag; a `<template>`'s content, a fragment the DOM never shows, is dropped; and, from the review's
   round 4, a `<title>` block the document begins with, which the parser puts in the head so nothing of it shows, is
   read as its text (a `<title>` anywhere else keeps its text in the DOM, so the tag is not in `DROPPED_CONTENT`); an
   RCDATA element left open across blocks (`<textarea>`, `<plaintext>`) is read to its block's end where the parser
   reads on; an inline `<textarea>` or `<title>` shows marked's HTML for the tokens inside it, decoded
   (`Parser.parseInline`: `<b>b</b> <em>c</em>` for `<b>b</b> *c*`, where round 3 read the tokens as markup); inside
   an `<svg>` or a `<math>` the raw-text rule is off (`FOREIGN`), so an svg's `<title>` is an ordinary element closed
   by its own end tag or the svg's (round 3 read `<svg><title>inner title</svg> beside` as the title's text to the
   block's end); and a raw html table's cell boundary reads a blank, the one `hayRuns` puts between two adjacent table
   parts (`TABLE_PARTS`), so a quote across `</td><td>` matches where it read the cells run together.
   `stripMarkupMapped(s)` is the rendered text of `s` read as a document of its own (`buildSourceTable`, beside the
   cached `sourceTable`), and `renderedQuote(source, range)` is exported for the corpus test. The hole reasons are
   constants (CODE_HOLE, INDENTED_CODE_HOLE, TABLE_HOLE), their strings unchanged. The list inherited from the strip
   at the build is closed: a code line opening with three backticks inside a longer fence has been code since the
   review's round 1 read the fence lines by offset, the `*` pairing across two cells and the `\|` inside a code span
   in a cell since round 2 read a row cell by cell, and a code line beginning `>` inside a QUOTED fence since round 3,
   the container's markers coming off through the walk's suffix view (the quote-marker rule had taken the line's own
   `>`); so are the constructs round 2 left, the rule of 3 and punctuation flanking, html entities, the shortcut
   reference link and the bracketed label, which the pipeline reads as marked does (a formula inside a cell stays
   routed to Slice 8, item 10 (j)). A range spanning prose and a hole is placed by the exact path from its positioned
   characters, the hole at the edge unpainted (item 10 (b) below), so the mixed-kind needle matters only for a range
   with no positioned character, where both sides agree line by line. anchor-map-fallback-markup.test.ts (25; six new,
   main's projection case, which the merge of main 6aef10815 appended after them, two from the review's round 1: a
   code span's content in a cell and a quote begun inside a fence line, with the strip's case list extended, and four
   from its round 2: same-delimiter nested emphasis in a cell, the code span with an escaped pipe and the backslash
   parity of a delimiter, the escapes with the inline tag, the mark, the wikilink, the strong-then-underscore and the
   cell's trailing backslash, and the fallback widening to the whole text when the range's blocks are paired to nodes
   that do not hold the quote; test 1's case list extended again, and test 6's count-guard scene, an html block whose
   attribute repeated its text, re-aimed at an entity spelling the text, since the strip now drops a tag with its
   attributes as the rendering does; anchor-map-change-marks.test.ts test 6's scene the same; and from its round 3:
   test 1 rewritten against the stand-in's rendering, test 6 re-aimed, the entity in an html block now painting by
   ordinal and a refused block whose node shows the passage twice staying unpainted over the whole text too, test 16's
   parity assertion on the unmatched backticks the cells show, and five new: the 300-cell seeded corpus as cells and
   as refused paragraphs, each read as the rendering shows it and painted whole, the 110 hand cases of rounds 1 to 3,
   the prose shapes a cell cannot hold, hard breaks, soft-break constructs and the code span's backslash, the cut
   ranges, `bold words** more`, `2024. It was`, `# of items`, the `3. ` continuation and a cut escape, and the html
   blocks, `costs \$5 raw`, `C:\Temp\</div>` and a `<script>` inside; the corpus fails over b1c6cb303 on 488 of its
   600 checks and the hand cases on 185 of 220; and from its round 4 the verdict's pin, `corpusVerdict`: the failure
   message counts failing checks against twice the cell count, each half against the cells and the distinct failing
   cells, where it had counted both halves against the cells alone, 300 of 300 with the prose half alone failing;
   anchor-map-change-marks.test.ts test 6 moved its count-disagreement scene to a rendering that gained a copy of the
   passage and pins the entity scene as painting the second shown `note`), anchor-map-html-text.test.ts (7, new in the
   review's round 4, each red over a git archive of 50b19bfdb: the minified raw table across cells and rows, the
   spaced table and a table inside a dropped script; block and inline `<foreignObject>` dropped with svg `<text>` and
   `<desc>` kept; the named references, the aliases, the legacy forms in a block and their literal reading in a
   paragraph, the case-sensitive table; the numeric reference quirks with the map's length equal to the text's; the
   inline `<textarea>` in a paragraph and a cell, an inline `<title>`, the block form and the open textarea; and the
   svg `<title>` in foreign content with a style inside an svg dropped), anchor-map-code-table-paint-browser.test.ts
   (4 legs over the real viewer and panel: a Raw drag over each passage saved through the float and the composer, the
   posted anchors the exact slices, then the switch to Rendered painting the code line whole inside the fence's first
   row and one mark in each of the row's two cells, each card offering Scroll and not Reveal; the same comments served
   before a fresh open, on the pane and in the chat modal; and, the review's round 2, Raw comments on the round 2
   cells, the nested emphasis, the code span with an escaped pipe, the escaped asterisks, `costs \$5`, the underscore
   beside a strong, an inline tag's text and a cell ending in a backslash, served before a fresh open and painting as
   the cells show them, every mark in its cell and each card offering Scroll; and, its round 3, 39 Raw comments on the
   round 3 shapes served before a fresh open, each painted with Scroll, `_snake_case_` among them, which round 2 had
   painted with 0 marks and no Scroll). The store's side: tools/file-comments-host-anchors.test.mjs (2 guards) and
   tests/test_file_comments_e2e.py (2 cases) pin that uniqueAnchor, locateExact and the comment verb, over the kernel
   wire, keep the slice with its operator or its delimiter and stamp anchorAt; the host was byte-exact before the
   slice, so both say they are guards.
5. *Item 3, the Raw offer at a formula, and refusals in the person's terms* (rulings 7 and 9). The math holes and the
   formula refusal landed with Slice 4 (its note, item 2), but `formulaExtra` took the Raw range from the selected
   RENDERED text, and KaTeX's glyphs are not in the source: Switch to Raw preselected the prose the drag ran into
   (`math and`) or nothing for a formula selected alone. Now, when the formula's hole is found, the offer is the
   hole's span with its delimiters, `$E = mc^2$` or the `$$` block through its closing line (the line feeds a display
   block's raw carries after it, and any indent before it, trimmed), rawHasQuote true and rawRange on
   blockStartOffset's line: equal to it for an inline formula or an unindented block, and past the indent for a
   display block written with one to three spaces before its `$$` or `\[`, where blockStartOffset stays at the hole's
   raw start, the indent, as before the slice (the review round 1 corrected this note, which had recorded the two as
   equal, and pinned the indented shape); rawTarget (file-comments.ts) searches for the slice from blockStartOffset
   forward, so the switch preselects the formula either way and the composer quotes it with Save; where the hole is
   not found (a hand-typed `.katex` placeholder before the real formula makes the count disagree; a formula under no
   block) the offer falls back to the selected text's occurrence as before, pinned. Six message sites carried a token
   type (`a ${t.type} the mapping could not place` in the inline walk, the block walk and the token placement,
   `${t.type} marks the mapping could not place`, and two defaults with `(${t.type})`). `refusalNoun(type, inline)`
   gives each token its noun: the Slice 4 constructs by what they show (a footnote definition, a footnote reference, a
   display formula, a formula, the front matter, a callout, a highlight for `mark`, a wikilink), marked's built-ins
   with their article (a paragraph, a heading, a list, a list item, a table, a code block, a quote, a rule, blank
   lines, a link definition, text, an escaped character, an inline code span, emphasis, strong emphasis, a
   strikethrough, a link, an image, a line break), `html` as an HTML block or, inline, an HTML tag, and "content" for
   a kind the map has no name for; the sites read `${noun} the mapping could not place` and
   `${noun} whose marks the mapping could not place`, and the defaults are the constant "content of a kind the mapping
   does not handle" with no type. No input the lexer accepts today reaches those sites (every token raw tiles the
   source; fifty odd shapes probed produce only refusals in the person's terms), so the closure is held by the
   catalogue through a test-facing export and by a source pin (anchor-map.ts interpolates no `${t.type}`); the refusal
   sentence's shape is untouched, so the guide's pinned clause and the composer pins stand. A selection that covers a
   formula WHOLE is prose holding a formula, not a selection inside one (the owner's ruling, the review's round 2): a
   boundary at the formula's first character at the selection's start, or at its last at its end, with the other end
   outside the formula, and a boundary outside the formula with only white space between them (`formulaBeside`: the
   first thing on the selection's side of the boundary, elements descended into, when it is a formula) map through the
   prose path with the formula's source inside the quote, its delimiters with it (`formulaHole` and `formulaSpan`,
   factored out of `formulaExtra`), so a selection of a paragraph that opens with a formula from its start, the (p, 0)
   shape a Range can take, or a drag from the formula's first glyph to a word after it, quotes
   `$E = mc^2$ opens this paragraph...` (before: refused as the formula, the Raw view preselecting the formula alone;
   in headless Chromium a REAL triple-click on the words anchors on the text after the formula at 0, so the words
   alone map, and one on the glyphs anchors inside them and is refused as the formula: the review's round 3 measured
   this, where round 2's note had said the triple-click anchors on the paragraph before its first child); since round
   3 `formulaBeside` covers a formula only when it lies before the selection's other boundary, so a selection of
   whitespace alone beside a formula is refused as whitespace and not as touching the formula (round 2 had named the
   formula and offered it in Raw); only a boundary strictly inside a formula is the formula's, and a formula covered
   whole with no text beside it in the selection (a triple-click on a display formula, or on a paragraph that is a
   formula alone) is the formula's still, through `orFormula` (item 4). Gesture facts for the formula legs, probed in
   Chromium: a drag begun at the centre of a lone KaTeX glyph collapses to a caret (five shapes probed), so a leg
   drags from inside the glyphs into the prose or from the prose into them; over the first glyph of `$E = mc^2$` the
   left fifth of the `x` box lands the caret at the formula's first character (covered whole, maps), its middle at the
   superscript's `2` at 0 (strictly inside, the formula's) and its right fifth at the `2`'s end (none of it); and a
   page over real-viewer-leg.ts needs KaTeX's sheet added, since the leg drops the sheet's import.
   anchor-map-obsidian.test.ts (28; five new: the offer in each of the fill's three shapes, inline and display, and
   over an indented display block (the review round 1); the placeholder's fallback; no token type in any refusal over
   the obsidian and refusals fixtures and 46 odd constructs, a case in the catalogue for every type the lexer emits
   over a kitchen-sink note and every extension name, the misplaced footnote definition's sentence, the source pin;
   the first obstacle, item 4; and, the review's round 2, the formula-first paragraph selected whole or from the
   formula's first glyph, a range begun strictly inside the glyphs still the formula's, a range ending exactly at a
   closing formula's last glyph covering it, and a display formula covered whole with no prose beside it the
   formula's; and, its round 3, the space after a formula, the gaps before a formula-first paragraph both ways and
   before and after a formula-alone paragraph, in the fill's three shapes, refused as whitespace while the covering
   shapes still cover), md-config-math-map-browser.test.ts (6; one from the build over the real viewer and panel on
   the pane and in the chat modal: a real drag from inside the inline formula's glyphs into the prose and a real
   triple-click on the display formula, refused with the Raw button promising the passage, the switch preselecting
   `$E = mc^2$` or the `$$` block in view, the composer quoting it with Save; and one from the review's round 2 over
   the real Files bundle: the triple-click's shape on a formula-first paragraph and a range from the first glyph to a
   word map with the formula's source inside the quote, a range begun strictly inside the glyphs is the formula's, a
   drag ending at a closing formula's last glyph covers it, and a REAL triple-click on the paragraph selects the words
   after the formula and maps them, the formula's source outside the quote, as Chromium's paragraph selection leaves
   the leading inline-block out of its range, the anchor pinned as the text node after the formula at 0 since the
   review's round 3).
6. *Item 4, the first obstacle in document order.* mapRenderedSelection ran a loop over the span's blocks for a
   REFUSED block and only then read the characters for a hole, so a visible html block anywhere in the span was named
   over an earlier table or code hole (the probe: a table cell or the math paragraph dragged to a `<details>` summary
   read "an HTML block" at the summary's offset where the table came first). Now one pass over the blocks from the
   span's first to its last names the first obstacle it meets: a refused block with an element on the page refuses
   when reached, a mapped block's selected characters are read for a hole before the next block is considered, a
   refused block with no element (a comment, a closing tag alone) is passed over as before, and the characters are
   read only when the endpoints stand in order, so the whitespace between two blocks is still "only whitespace" and
   the block beside it is not scanned. blockExtra and rawExtra are unchanged, so each refusal's Raw offer is what it
   was; the two probe scenes name the table with the table's Raw offer, and the paragraph before a div into its nested
   paragraph still names the HTML block, the wrapper's block being the first obstacle (item 1). A formula at the
   selection's END is an obstacle like the others, named in the pass (the review's round 1: `formulaEnd` defers the
   end's formula check to after the document-order pass, so a span from a table cell, or from the intro across the
   table, into a formula's glyphs names the table with the table's Raw offer; a formula at the START is the first
   obstacle and is named at once; the early refusals for a selection the text cannot place or of whitespace alone
   yield to the formula when the end is inside one, so a drag from the space between two formulas into the second
   names the second, and to a formula the selection covers whole with no text beside it (item 3, the review's round
   2); before, the formula check at the top named the formula ahead of the table). anchor-map-obsidian.test.ts (a note
   with a code block, a table and an html block), anchor-map-wrappers.test.ts (the two scenes over wrappers-plain.md,
   the code line past the div wrapper naming the code block, and the formula at a selection's end over a note with a
   table and two formulas).
7. *Item 5, opening `<details>` ancestors in goTo: landed with Slice 4* (revealMarks in file-comments.ts, run first in
   goTo, in scrollCard and before the pass for a card the head click opened;
   md-config-goto-closed-details-browser.test.ts and the two focus plan pins hold it). Nothing built here; the guide
   gains the sentence (item 10). In the list layout a card-head click toggles the card and reveals no fold, by design
   (the reveal runs on the head click in the margin layout alone; the quote button reveals in both layouts); left as
   it is, since a head click in that layout has never scrolled.
8. *Item 6, overlapping highlights: one wash, a click opens every covering card* (ruling 3: every covering card opens,
   the clicked one is the focus, no chooser). The later-painted comment nests inside the earlier one's mark wherever
   they overlap (wrapNode wraps each text node in place; the pass paints in cards() order and repaintPresel keeps it),
   so the delegate resolved the innermost mark, fcopen opened that one card, and the outer card could not be reached
   from the overlapped text; the sheets had no nested rule, so the overlap composited a second wash and a second inset
   ring. Now the fcopen handler, after the dragClick guard, opens the cards of every comment whose highlight covers
   the clicked mark (`openCovering`: each fcopen mark of the panel's own above the clicked one, opened as a head click
   opens a card, in one render) and shows the clicked one as the focus (showCard, level with its mark in the margin
   layout); Enter on a mark takes the same path through the row's keydown, KEY_ACTS an exact set still. Both sheets
   gain `.fc-hl .fc-hl { background: none; box-shadow: none; }` byte-equal, the head in the fileview-parity RULES
   list. The rule drops the wash and the ring only: the padding stays, so every wrap point stays where the nest legs
   measure it (the layout-neutral mark, item 10 (f) below, is the person's call, not applied); the dashed context cue
   is an outline and stays; the arrivals dot's rule comes later at the same weight and stays. With a composer pending
   on a target in the same line, the repaint has painted the highlights again in cards() order with the target among
   them: the nested mark is still transparent, the click opens both cards, and in the margin layout the pending
   composer's box holds the slot level with its target so the cards stack under it, the clicked first; that stacking
   is the margin layout's standing rule, and a clicked card level with its mark while a composer stands would be a
   card-layout question, not this item's. file-comments-overlap.test.ts (5), file-comments-overlap-browser.test.ts (1
   leg over the real panel at 900 and 600 px: the nested mark's computed background transparent and no ring while the
   outer keeps both; a real click on the overlap opening both cards, the clicked one level with its mark in the margin
   layout and both open in the list; the same pending and after Cancel). tools/file-review-plan-markclick.test.mjs's
   pin on the handler line is re-aimed with its intent.
9. *Item 7, paintAll's sequential hint, the narrow version* (ruling 4: build it and move the four verbatim pins with
   it, an inserted line not sparing the two regex pins that require the lines adjacent). paintAll hands the engine a
   card's stored position as the tie-break; a card with none (written by the CLI or another editor) took no hint, so
   two such comments with the same anchor on a repeated line both painted on the first copy. Now such a card takes a
   sequential hint when a card painted before it in cards() order has the same anchor, equality being the quote with
   its prefix and suffix (`anchorKey`, the host's own reading of a tie): a position whose nearest tied copy is the
   first copy AFTER that card's (`nextCopyHint`). The engine breaks a tie by the copy nearest the hint, so the
   previous card's located end alone, the shape first proposed, would name the next copy only when it starts within a
   quote's length of that end, a repeated line; the probe steps the hint right from the previous copy's start,
   doubling the distance, until the engine's pick moves past that copy, which the doubling keeps at or short of the
   next copy, so the pick is that copy and never one beyond it, in log2(gap over quote) engine scans, one scan when no
   copy follows and then no hint (the engine's earliest pick, as before); a repeated paragraph is covered too, and the
   rule is still narrow, positionless cards with an equal anchor alone paying the scans. copyUnsure still receives the
   STORED position, never the hint, so the pick stays a guess: the dashed cue, the "passage recurs" tag, the mark's
   title saying no position is stored, and, for a card the hint placed, the mark's title, the tag's title and the open
   card's line naming the copy after the previous comment's on this passage rather than the first (`copyUnsureWords`
   and `unsureMarkTitle` take `hinted`, from `Panel.hintedCopies`, set in paintAll when the stored position is
   undefined and a hint was made; the review's round 1: a hinted card's words named the first copy while its highlight
   sat on the second); a card with a position is unaffected wherever it stands, and a unique anchor takes no hint. The
   pins moved: file-comments-anchors.test.ts, tools/file-review-plan.test.mjs,
   tools/file-review-plan-anchors-states.test.mjs (its includes on the unsure line stands).
   file-comments-hint-order.test.ts (4: three copies a thousand characters apart with two positionless comments on the
   first and second, one positioned on the third unaffected, a fourth with no copy left back on the first, a unique
   anchor plain; the hint scoped to an equal anchor; the probe's back-to-back line with a two-character context; the
   words for each copy on the mark's title, the tag's title and the open card's line, the review's round 1). The
   branch's second merge of the fork's main (213fde5fa, 2026-09-11) put the host's confirmed copy before both:
   paintAll's hint is now the copy the host's tie-break confirmed (`placedAt`, the file-review plan's decision 51),
   else the stored position, else the sequential hint, and the words for a guessed copy name the confirmed place
   first, then the hinted copy, then the first copy, then the copy nearest the stored position (`hintedCopy` rides on
   the card as `confirmedAt` does, stamped by renderCard and by paintAll for the mark's title; the four pins moved
   again with it).
10. *Item 9, the Comment offer on a keyboard selection* (ruling 6: the listener lives in the panel, not the seam,
   whose onSelect also seeds the quote chip with a fetch of the file per gesture and must not run per keystroke). The
   float rode the seam's mouseup and touchend alone, so a selection made or changed from the keyboard (Shift+Arrow
   over a drag's selection, caret browsing, assistive technology) offered nothing and the float stayed where the drag
   had left it while the selection shrank under it. The panel now hears the document's selectionchange
   (`onSelectionChange`), installed after the seam's hook line (file-view-place.test.ts requires the body's scroll
   listener line immediately followed by that hook) and removed at dispose, with four guards and then the seam's own
   path (onSelection): nothing while a pointer is down (`pointerHeld`, set by the capture mousedown of the PRIMARY
   button and by touchstart beside hideFloatOnDown, cleared at mouseup, touchend, touchcancel and dragend, since a
   press that becomes a native drag of selected text sees no mouseup, and, since the review's round 2, at the
   document's contextmenu and the window's blur, pressHold's shape in actions.ts: a right or middle press selects
   nothing and often ends in no mouseup, Chromium on Linux and macOS handing the release to the native menu, so a flag
   it raised stood until the next left click and every keyboard change of the selection in between offered nothing,
   and a contextmenu or a blur means the browser ended a primary press itself; a drag keeps its one offer at mouseup
   and the float does not flicker mid-drag); nothing while the editor holds the body; the selection the float answers
   to changes nothing (`offeredFor`, its text and two ends, recorded by onSelection and re-read from the live
   selection after every paint of the panel's own, `afterPaint` at the end of paintAll and of repaintPresel and at
   paintAll's stand-down while the editor holds the body, so the seam's re-seat of the same ends after a reflow makes
   no second offer, an offer a scroll hid stays hidden, a scroll firing no selectionchange, and the paint's own move
   of the selection is no offer either: unwrapping a mark collapses a selection end inside its text to the mark's
   place, so a selection overlapping a highlight is cut short by every paint that is no gesture of the person's, a
   peer's comment landing through the poll among them, and the browser fires selectionchange for the move, which a
   record of the OFFER's ends read as the person's and re-showed a hidden float beside a passage nobody selected; read
   after each paint, the record also holds no node of a swapped-out render, where it used to keep the offer's nodes,
   and the render behind them, until the next offer; the guard compares the four ends first and reads the text once,
   for ends that match, handing it to onSelection; the review's round 1); a collapsed selection, or one with an end
   outside the body (Ctrl+A puts one at the page's start; a selection in the aside), HIDES a passage's float
   (`passageGone`, the listener's rule), one point beyond what was first designed, which had the outside-body case do
   nothing (the passage the float was offered for is no longer the selection; a picture's float stands), and since the
   review's round 4 drops the record of the offer with it (`offeredFor` nulled), so the selection the keyboard brings
   back to exactly the offered ends is a new selection and offers (before, Shift+ArrowDown carrying the focus into the
   aside hid the float and the Shift+ArrowUp after it, back at the ends of the last offer, read as the selection
   already answered and offered nothing; the scroll's hide keeps its record, so the re-seat of the same ends after it
   stays no offer), and afterPaint applies the same rule to the panel's own paints (the review's round 2: a highlight
   that is its paragraph's whole text is the `<p>`'s only child, so the unwrap and the wrap again of its mark collapse
   a selection inside it to the paragraph and Chromium fires no selectionchange for that move, a merged or split text
   node being what fires it, so a peer's comment through the poll or a settings pick from another pane left the float
   standing beside nothing; a float beside a selection cut short but not to nothing stays where it was offered); a
   different non-collapsed selection inside the body shows the float at its rect. The quote-chip seed stays on mouseup
   and touchend; the seam comment at file-view.ts onSelection says where the keyboard's path lives. In Chromium a
   keyboard selection needs an existing selection or caret browsing (F7), so the gain is the float following a
   keyboard-adjusted selection and the offer for caret-browsing and assistive users.
   file-comments-keyboard-offer.test.ts (10; two from the review's round 2: a right or middle press raises no flag and
   the next keyboard change offers, a primary press is over at contextmenu and at the window's blur while a touch
   press holds to touchend, and the dispose case counts the contextmenu and blur listeners' install and removal; one
   from its round 4: the passage-gone hide drops the record, in its aside and collapsed faces, the scroll's record
   kept), file-comments-keyboard-offer-browser.test.ts (3 legs over the real panel: at 380 and 900 px a drag, then
   Shift+ArrowLeft three times, the float at the shrunk selection's own rect, a text-size step leaves it hidden, the
   next keyboard change offers again at the reflowed rect, Ctrl+A hides it, a drag offers once more; and, the review's
   round 2, a right-button press whose release the page never sees, then Shift+ArrowRight offering at the selection's
   rect, and a left press ended by a dispatched contextmenu with no mouseup, then the same; and, its round 4, at 800
   by 650 px over a thirty-paragraph note, a drag of the last paragraph, Shift+ArrowDown until the focus leaves the
   body, each press awaited on a selectionchange and the float asserted beside each in-body extension, the float
   hidden with the focus in the aside, and one Shift+ArrowUp landing at exactly the kept ends, by node identity and
   offsets, offered again), file-comments-paint-offer.test.ts (4; three from the review's round 1: the float across a
   paint that cuts a live selection, a WeakRef over the offer's text node collected after a reload, and one toString a
   change; one from its round 2: a paint that collapses a live selection to nothing with no selectionchange hides the
   float, the next change offers, a selection cut short keeps it and a hidden float stays hidden) and
   file-comments-paint-offer-browser.test.ts (2 legs over the real pane: a peer's comment through the real poll cuts a
   real drag's selection, the hidden float stays hidden and a shown one stays put, and Shift+ArrowRight offers; and,
   the review's round 2, a comment over the whole of a paragraph, a real drag inside its mark and a peer's comment
   through the poll collapsing the selection with 0 selectionchange events, the count asserted since the review's
   round 3 (a browser firing one for the collapse would hide the float through the listener's rule and the leg would
   pass without reaching afterPaint's), the float hidden, then a fresh drag and Shift+ArrowRight offering at the
   widened selection's rect). The same round found four of the panel's node tests reading the selection through
   per-test fakes that asserted their world's nodes at call time, or pinning paintAll's shape:
   file-comments-about-review2 and file-comments-markclick-controls read their fake once, and file-comments-regions,
   file-comments-reveal-landing and file-comments-behavior pin the pass with afterPaint in it.
11. *Item 10, the records, and what was routed here from Slice 4.* docs/guide.md's Comments paragraph gains three
   clauses (the button follows a keyboard selection; two comments over one text carry one highlight and a click on the
   overlap opens both cards, the clicked one in front; going to a comment inside a closed fold opens the fold first),
   pinned by tests/test_guide_files_keyboard_overlap_fold.py against the source that keeps each; the vocabulary and
   anchors pins' clauses stand where they were. From the review's round 4 (2026-09-11) one change outside the slice's
   units, in the sanitizer, pre-existing on main: an html comment is dropped by `dropCommentChildren` (md-sanitize.ts,
   on a `uponSanitizeElement` hook) before DOMPurify judges the element holding it, because DOMPurify's SAFE_FOR_XML
   markup guard read a comment's `<!--` in the innerHTML beside a literal `<word` (`&lt;x&gt;`, which reads `<x` in
   the textContent) and removed a `<p>` or a `<td>` whole with its prose (the seeded corpus's cell 346 rendered as a
   row with one cell and a comment on it painted nothing); no other output changes, since DOMPurify drops every
   comment on its own, later in its walk, and the guard itself is untouched; md-sanitize-comments-browser.test.ts (2,
   new) over the viewer and the chat's sanitizeMd call, md-sanitize.test.ts (15: the hook count, the hook body over a
   fake node, the guide sentence) and docs/guide.md's HTML paragraph gains one sentence, an HTML comment is dropped
   and the text around it is kept. The ledger entry is upstream/2026-09-10-markdown-viewer-slice5.md (tier feature).
   CONTEXT.md is unchanged: the build coined no term (a wrapper is the Slice 2 note's own word for the element the
   browser nests markdown into). From the Slice 4 note's item 10, decided with the build: (a) the html-block resync
   defect, its same-text trigger closed by item 1c's tag test and its sanitizer-shortened trigger by item 1's
   closed-tag rule, the trim leg's confinement lifted; (b) a hole at a range's edge stays unpainted and the callout
   title stays text, the rule as it stands with its two pins (anchor-map-obsidian.test.ts: the alert body maps, a
   nested fold's title inside the range is painted with the rest), since painting a hole at the edge would paint
   tables and code blocks there too and is Slice 8's neighbourhood; (c) the whitespace alphabet at a selection's edge
   stays JavaScript's `\s` on every side, since a narrower one is a change to the walk, the matching and the panel's
   normalize together and nothing here needs it; (d) the unpaint normalizes each parent once: `unwrapMarks(marks)`,
   exported from file-comments.ts beside unframeImage, collects the parents over the loop and normalizes each after it
   (the 9,999 marks over the 5,000-link paragraph unwrap in 11 ms against 469 while the browser has not laid them out;
   the panel's own unpaint always finds them laid out and pays about 340 ms against about 790 there, Chromium's
   detachment of each mark's layout object being the rest, 2.3x and not 40x: the review's round 1), Panel.unpaint and
   Panel.unwrap (repaintPresel's step) run it, nested marks coming outer first so the inner's parent is the block by
   the time it is read (given inner first the detached outer's normalize is a no-op and the block is still normalized
   once); file-comments-unpaint-normalize.test.ts (2, the normalize counted per element) and
   md-config-paint-whitespace-browser.test.ts's timing legs re-aimed at the panel's own function in place of their
   private copies; (e) a display formula under a highlight stays bare, decided with Slice 8's block-level paint; (f)
   the layout-neutral mark not applied (item 6); (g) paintPresel untouched, nothing to record; (h) the list layout's
   head click unchanged (item 5); (i) Slice 8's boundary stands: a cell or a code line selected from Rendered refuses
   with the Raw offer and the switch preselects the passage, a selection across two cells refuses with no preselect,
   and item 4's one pass changes neither (one obstacle in those spans); (j) routed to Slice 8 from the review's round
   2, no code here: a formula inside a table cell gets no Raw preselect, since the table is one TABLE_HOLE whose cells
   the walk never enters, so the offer is item 3's recorded fallback, the selected text's occurrence, and a drag from
   the formula into the next cell preselects that cell's text; and a Raw comment on such a cell paints nothing, the
   hay dropping the formula element as a control while the needle keeps its TeX (item 2); both fall out of Slice 8's
   exact cell mapping (its brief's section 2 (k)); and, from its round 4, the formatting element a paragraph leaves
   open (item 1's not-modelled list, with its `Block.leaves` fix shape) to Slice 8's pairing work (the brief's section
   2 (l)). Recorded as a follow-up of no slice, from the same round: a quote inside an svg `<title>` counts as
   painted, since `runsUnder` reads the title's text into the hay and the trim keeps a non-blank mark with no box for
   the closed-details reveal (Slice 4's rule), identical on main; the fix is a hay rule for SVG's never-rendered
   elements (`<title>`, `<desc>`, `<metadata>`); and an HTML `<mark>` wrapped around svg `<text>` content removes that
   text from the rendering, on main and here alike. Also decided: one PR for Slice 5 alone, Slice 8 to extend its test
   files; the new node tests in the test-DOM shim's idiom (hideEdges on every node, as the ratchet requires) with the
   existing stand-ins left unswitched for fork PR #569's migration, which the merge of main 6aef10815 then brought in
   (2f79481b: the blocks and fallback-markup stand-ins call hideEdges and carry a projection case each, the ratchet's
   allowlist empty with ALLOWLIST_MAX at 0); the two paint calls, the class line, the onSelection wiring,
   switchToRaw's body, the panel's CSS block, the KEY_ACTS set, goTo's selector and the reveal lines keep their
   source-text pins, none moved but item 7's four and item 6's one. Costs recorded: the tag scan is linear in an html
   token's raw and runs once per source on the Walked row (the one Lexer.lex across three roots stands,
   file-view-place-source-cache.test.ts); the wrapper's cost to a mark is item 1's measurement, at or under a flat
   note's since `blockTopOf` (the review's round 1); the sequential hint costs one engine scan for a positionless
   same-anchor card whose copies are used up and log2(gap over quote) plus one otherwise, paid by such cards alone;
   the descent costs one shape check per level read, not one per top-level child (item 1b); the nested mark rule
   changes no box the trim or the margin layout reads; the Raw read lexes and parses the top row's block on every
   scroll frame while that block is an html block, closing tags alone and comments alone excepted (the review's round
   2): readPlace runs once per scroll frame in Raw (file-view.ts notePlace, one read per animation frame) and runs
   `readsAsNext` on the top row's block, on each block of a run after it and on each block after a fold the place
   carries (`foldStands`); `readsAsNext` runs `closesAlone` and `isCommentBlock`, a scan each over the block's text,
   then `opensWrapper`, which lexes a block opening with `<` alone (`isHtmlBlock`, one Lexer.lex) and parses an html
   token's block with DOMParser, the block's source with the probe paragraph appended, and nothing of it is kept
   between frames, so a paragraph's row costs the three tests alone: counted over the real viewer in the review's
   round 3, one frame per single-pixel scroll step, one lex and one DOMParser parse per frame with a centred div
   wrapper's opener row on top (12 in 12 frames), two of each with its `<img>` row on top (24 in 12, counted again in
   the review's round 4: readPlace's Raw branch asks `opensWrapper` once more for the row's block, for `Place.pic`,
   item 1b) and none with a plain paragraph, a nested paragraph or the `</div>` closer row on top; the fold table
   (`foldDepths`) is one pass over the blocks per source, kept for the last source read as the anchor map keeps its
   block table, so a frame over unchanged text reads the table without rebuilding it (the review's round 2); in the
   fallback (item 4) `renderedBlocks` writes out the scope's blocks once per fallback paint, linear in the scope's
   source, through the lexer's cached tokens (`sourceTable`), and the whole document once more when the count guard
   widens (the review's round 3, in place of round 2's bounded emphasis passes over the strip). Tests, by file (every
   new node test on the shim's stand-ins with hideEdges; every browser leg over headless Chromium and the real
   bundles, 0 skipped, counted on every run): anchor-map-wrappers (34, four from the review's round 1, five from its
   round 2, eight from its round 3 and seven from its round 4, test 27 re-aimed), anchor-map-html-text (7, new in the
   review's round 4), anchor-map-wrappers-browser (6, one from the review's round 2, the panel open over a bare
   `<img>` block, and two from its round 3, the wrappers' leftovers and the open `<p>`), anchor-map-fallback-markup
   (25, six new, main's projection case, two from the review's round 1, four from its round 2, five from its round 3,
   the corpus among them, and its verdict's pin from its round 4), anchor-map-code-table-paint-browser (4; its cards
   opened from their heads before Reveal's absence is read, the review's round 1; the round 2 cells, its round 2; the
   round 3 shapes, its round 3), anchor-map-obsidian (28, five new, the review's round 2's formula-first paragraph and
   its round 3's whitespace beside a formula), md-config-math-map-browser (6, one new and one from the review's round
   2, its real triple-click re-aimed in round 3), anchor-map-change-marks (7; its count-guard scene moved off an
   attribute's text in the review's round 2 and onto a rendering that gained a copy in its round 3),
   md-config-paint-trim-browser (5, the confinement lifted), the fixtures anchor-map-fixtures/wrappers-plain.md,
   wrappers-2block.md, wrappers-unclosed.md (new) and blank-scenes.json (its note); file-view-place-blocks (14, two
   rewritten and main's projection case), file-view-place-html-browser (10, two rewritten, two from the review's round
   2, one from its round 3, one from its round 4), file-view-place-wrapper-end-browser (3, two rewritten),
   file-view-place-edits-browser (4, one tightened), file-view-place-closed-details (9) and
   file-view-place-closed-details-browser (10, both the review's round 1, extended in its rounds 2 to 4);
   file-comments-overlap (5), file-comments-overlap-browser (1), file-comments-hint-order (4, one from the review's
   round 1), file-comments-keyboard-offer (10, one from the review's round 4), file-comments-keyboard-offer-browser
   (3, one from its round 4), file-comments-paint-offer (4) and file-comments-paint-offer-browser (2; the paint-offer
   pair the review's round 1, all four extended in its round 2, the browser leg's event count asserted in its round
   3), file-comments-unpaint-normalize (2), md-sanitize (15, two and the hook count from the review's round 4) and
   md-sanitize-comments-browser (2, new in its round 4), fileview-parity (the nested head), file-comments-anchors and
   md-config-paint-whitespace-browser (re-aimed), file-comments-behavior, file-comments-regions and
   file-comments-reveal-landing (pins on paintAll's shape re-aimed) and file-comments-about-review2 and
   file-comments-markclick-controls (their selection fakes read once); tools/file-review-plan.test.mjs,
   tools/file-review-plan-anchors-states.test.mjs and tools/file-review-plan-markclick.test.mjs (pins moved);
   tools/file-comments-host-anchors.test.mjs (14, two new), tests/test_file_comments_e2e.py (25, two new),
   tests/test_guide_files_keyboard_overlap_fold.py (8, new). Every case that changes behaviour fails over a
   `git archive` of a3edbaaf7 (the branch's base), of 40a4db43a for the review round 1's, of e5295ffa6 for its round
   2's, of b1c6cb303 for its round 3's, or of 50b19bfdb, the second merge of main, for its round 4's, and says how in
   its commit; the guards say they are guards. The guarantees the families re-verify: highlights are measured
   `<mark class="fc-hl">` elements over the range's text nodes with their data-act, id, tabIndex, role and title, the
   margin layout reading their boxes (the walk, the raw needle and the cell gap change where marks appear, never their
   shape; the nested rule their paint, not their boxes); the pairing is the one table the reader's place, the change
   marks and the selection map read; the regions layer's span over a picture is in the index's shape at every depth;
   PRE and TD stay refused, so the fallback's ordinal keeps marking the changed cell or line under the raw needle and
   the pipe rule; the float, the composer and the save keep their rules under the keyboard offer and the composer's
   quote stays the exact source slice; and Slice 8's boundary stands.

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
