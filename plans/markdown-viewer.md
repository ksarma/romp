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
   The gate itself ran after the sanitized nodes were adopted into the live document until 2026-09-20, and WebKit fetches
   an img on that adoption, so its placeholder stood over a request already made; the hole, the fix and its measurement are
   in "Fix: the gate before adoption (2026-09-20)", the section after "Out of scope".
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
   later updates this sentence and anchor-map.ts's header; Slice 8 deleted both instead, its mapping reading no row:
   the Slice 8 note, item 2). After: the two-line range paints marks in rows 0 and 1, the whole fence in its four text
   rows, a two-line range of a plain fence in both rows, an insertion across lines in two or more rows, and a Rendered
   selection inside code was still refused with the Raw offer (until Slice 8 positioned the code's characters; the
   leg's step 7 now asserts the mapping to the word's own offsets in the fence's line: the Slice 8 note, item 2).
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
   Since 2026-09-20 the chain runs on the sanitizer's own body, before the adoption into the live document: a chain after
   the adoption fetched a gated figure in WebKit while the placeholder stood ("Fix: the gate before adoption (2026-09-20)",
   the section after "Out of scope", records the hole, the fix, the instrument and the tests).
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
commit after the merge, 701728eae, and its round 5 as the commit after that and its round 6 as the one after it, each
round's findings in the build report's round section. A probe over the real viewer (2026-09-09, at 4def8dd8) recorded
each defect before the build, and the ten rulings of 2026-09-09 on the points the text above left open are cited below
by number with what each said. The items take the numbers of the sentence above, in the order it names them (the
parenthesis on `<details>` is item 5; the reader's place inside a wrapper is item 1b and the merge review's text-alike
node item 1c), and a reference to an item below is to that numbering. The standing rule for the build: these changes
cause the file-comments feature no trouble, which item 10's last entry states as the guarantees every test family
re-verifies. Where the code as built departs from the text above, why, and which test holds each rule:
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
   non-checkbox input passed over, an unwrapped one listed as its own children, which the unwrap leaves in its place
   (`topTags` flattens an UNWRAPPED element's kids into its parent's at its end tag, a `<textarea>`'s content as a
   text kid; the review's round 6: a `<button>` holding a badge picture or a `<form>` holding a `<b>` before the
   depth-1 wrapper left that element at k unread, the inner wrapper was not found and the nested paragraphs were
   refused as mismatches, a regression against 701728eae and, for the `<button><img>` badge shape, against main), the
   first the DOM does not hold as described ending the read), so the wrapper's own children are its block's without
   the resync and the next html block's scan starts at the first nested block (round 1's recorded edge closed:
   `<div align="center"><div>Lead</div>` then `<div class="in">`, and `<div><p>Lead</p>` then `<p>Alpha</p>` pairs the
   leftover to the wrapper). The run check reads a comment's mark over an unwrapped element's hoisted text as that
   text (`pastHoisted`, a run of text nodes and MARK elements whose text together is the block's `htext`; before, a
   comment spanning into a `<form>`'s lead unpaired every later block on the re-analysis). A block whose scan took
   nothing and whose run no end confirms hands the nodes back at the next html block's own element (`nextAnchor`, the
   blocks between passed over, `handedTo`; the element being, for a block that leaves no tag open, the first node of
   the block's first tag from which the blocks after the block line up through to the content's end or an html block's
   own element, past the nodes its own scan takes, `scanTake` and `runFits` with `toEnd`, else and when no candidate
   lines up the first node of the tag; the review's round 6: the first node of the tag was taken whatever followed, so
   an html `<p>Go</p>` block after a swallowed run of paragraphs was handed the first swallowed paragraph's `<p>`, the
   paragraph Go after it paired with the html copy, a selection in the html copy mapped to the paragraph's offsets and
   a comment made there stored on the wrong passage; and an html `<p></p>` block after the run took the run's first
   minted `<p></p>`, so it owned the run and the run's refusal carried its offset, past the passage, where the Raw
   offer's search from it missed), not at the document's end (a `<button>` opener whose paragraph's own `<button>`
   closes it now loses the paragraphs up to the next html block's element, or up to a block of closing tags alone
   (`</center>`), where the pairing resumes at the first end from which the blocks after it line up through to the
   content's end, or to an html block's own element (`runFits` with `toEnd`; past two confirmations the run reads one
   block that does not fit with its node, as the pairing loop pairs a mismatch: round 6, a paragraph the sanitizer
   shortened third or later in the tail after a `</center>` closer had ended the run at every candidate, the swallow
   ran to the document's end and every tail paragraph was refused as an HTML block where 701728eae and main mapped the
   others; and before two confirmations ONE such block is read the same way when the blocks after it line up with the
   nodes after its through to the end, a lookahead spent once, so no second unconfirmed mismatch is read: round 7, the
   shortened paragraph first or second in the tail had ended the run at every candidate too and the swallow ran to the
   document's end where main mapped the other three; the same lookahead confirms `nextAnchor`'s candidate after an
   html `<p>` block when the tail's first block is such a paragraph, where the first node of the tag had stood and
   owned a swallowed paragraph's `<p>`; two such blocks before two confirmations still swallow, recorded; and the
   review's round 8, three fixes: inside that lookahead an html block's element at k confirms nothing by itself, the
   run goes on past the nodes its scan takes and the blocks after must line up too, unless the block leaves a tag
   open, whose nested blocks pair against spliced children the run cannot see (the tag match had returned true one
   node early, so after a `</center>` closer a tail [paragraph, html `<p>`, paragraph] resumed at the node before the
   paragraph's, the paragraph mismatched it as the tolerated one, its own `<p>` stood for the html block's, the html
   block owned the run and the paragraph was refused as an HTML block at the html block's offset, where 78c0806ce and
   main mapped it, a regression; the README's `<p align="center"><img>` in the html block's place the same, and
   `nextAnchor`'s html `<p>` candidate before such a tail); in any run to the content's end an html block whose
   element stands BEHIND k is a misaligned run, not a dropped element, since a dropped or unwrapped element is nowhere
   in the content at all (two raw `<table>` blocks with a foster-parented `<br>` between their elements, then a
   paragraph the sanitizer shortened and a last paragraph: the second table's element had passed as the first table's
   candidate, the second table was read past as nowhere and the last paragraph was refused as an HTML block where
   78c0806ce mapped it, a regression); and a run whose content runs out while a block still needs a node is no run,
   main's rule (HIGH: since 552f2bc20 one confirmed block had passed it, so with a wrapper's nested blocks [P1, a
   paragraph the sanitizer shortened, P1 again] and nothing after, a README ending in a centred footer, the candidate
   end at the LAST copy passed, the wrapper's block took the first copy and the shortened paragraph, the first copy's
   block paired with the last copy, a selection in the last copy mapped to the first copy's offsets and a comment made
   there was stored on the wrong passage, where main refused both copies; for a `<div>` open to the end, a
   `<div align="center">` closed after the copy, a `<details><summary>`, a `<div>` closed right after the copy and the
   `<span/>` or `<div/>` round 7 opened; each copy maps to its own offsets now, the wrapper's block owns the wrapper
   alone and the shortened paragraph is a mismatch with its own `<p>`); and the review's closing pass, four fixes: in
   any run to the content's end an html block's element at k confirms nothing by itself until two blocks with text
   have confirmed the run, outside the lookahead too (fuzz8 seed 1330, HIGH: with a paragraph repeated inside and
   after a swallowed run and an html `<p>` after the second copy, the `</details>` resume's candidate at the first
   rendered copy had passed on the second copy's text and the html block's tag, the second copy's block owned the
   first rendered copy, a selection there mapped to the second copy's offsets and a comment made there was stored on
   the wrong passage, where 99e7e2d0c and main refused both copies; the second copy maps from its own `<p>` now and
   the first is the button's, refused); the behind-k scan runs over the run's own nodes from the candidate's index
   (`from`), not from the content's start (a kept `<input type="checkbox">` block before the swallow, or as the
   opener's own kid, had failed every candidate at a removed `<input type="text">` block in the tail and the tail was
   swallowed where 99e7e2d0c and main mapped it); the text an html block's raw puts at the top level after a tag
   (`<div>x</div> trailing text`, `TopTag.after`) is read past with the tag's element by `scanTake` and the pairing
   loop's scan (`pastAfter`, over `pastText`, the one read of a bare text shared with `pastHoisted` and `pastKids`),
   so the run to the end past such a block lines up where the shortened paragraph before it had been swallowed; and
   `topTags` reads the parser's adoption agency algorithm at a formatting element's end tag met with a special element
   open above it (`SPECIAL`): the formatting element closes where it stood and each special element above it leaves it
   for the element below and stays open with a clone inside, so `<div><b><p>x</b><div>` holds [b, p, div] as the DOM
   does and the nested paragraph and the paragraph after map, for `<b>`, `<a>`, `<i>`, `<strong>`, `<font>` and a
   README's centred wrapper, and a formatting element that is the top-level tag hands its `<p>` up as a top-level tag
   (a regression against 701728eae since round 5's depth-1 lookup, which met the reparented `<p>` where the inner div
   was expected; main refused both as an HTML block); a non-formatting element between the formatting element and the
   `<p>` (`<div><b><span><p>x</b><div>`, the span) closes inside the formatting element where it stood, so the shape
   maps the same, but a FORMATTING element between them (`<div><b><i><p>x</b><div>`, the i) is not modelled: the
   algorithm clones it too and moves the `<p>` into that clone, so the DOM's div holds [b, i'] with the `<p>`, the
   inner div and the markdown nested in it inside the clone, and the markdown after the wrapper sits in a second clone
   at the top level, where the scan lists [b, p] under the div and the inner div at depth 1; the depth-1 lookup meets
   the clone, the nested paragraph is refused as a mismatch, as on main, and the paragraph after maps (the review's
   closing pass 2, stated in `topTags`' docblock, recorded, not fixed); and the review's closing pass 2, three fixes:
   in any run to the content's end an html block's element at k confirms nothing by itself until two blocks whose text
   is UNIQUE among the blocks after the swallower, the ones whose nodes can be candidates, have confirmed the run
   (`repeatedFrom`, the texts more than one of those blocks carries, built per `nextAnchor` call and carried on the
   `ToEnd` record as `repeated`, and `runFits`' `unique` beside `confirmed`; the closing pass 2 built the set once
   over the whole document, and its pass 3, below, narrowed it): a repeated paragraph fits the wrong copy's node as
   well as its own, so it confirms nothing at a tag (HIGH: the closing pass's count of two was met by two paragraphs
   repeated inside and after a swallowed run, [F, G, `</details>`, F, G, an html `<p align="center"><img>`, ...], the
   `</details>` resume's candidate at the FIRST rendered copies passed on the second copies' blocks and the html
   block's tag, the second copies' blocks owned the first rendered copies, a selection in either first copy mapped to
   the second copy's offsets and a comment made there was stored on the wrong passage, where main refused every copy;
   each second copy maps from its own `<p>` now, the first copies are the button's and refused, the html block owns
   its own picture `<p>`, and where no candidate lines up the mapping refuses, as main does); the behind-k scan reads
   a `ToEnd` record `nextAnchor` builds per candidate (`bounds`: `from`, the candidate's index; `region`, the resume
   index k; `named`, the element names among the tags and kids of the swallower and of every html block passed over
   before the resuming block; `taken`, the indices the scans of the run's own html blocks consumed): a same-tag
   element among the run's own nodes from the candidate fails the run unless a scan inside the run took it for its own
   block (a kept `<input type="checkbox">` block in the tail before a removed `<input type="text">` block: the closing
   pass's two rules together had walked the run past the checkbox and failed every candidate at the removed input, so
   the resume fell to the checkbox block and the first tail paragraph was swallowed where 99e7e2d0c and main mapped
   it), and one among the swallowed nodes from the resume index fails it too unless the swallower's or a passed-over
   html block's raw names the tag (the closing pass had bounded the scan at the candidate, so after a `</center>`
   resume a candidate past the run's own first table, [two raw tables with a foster-parented `<br>` between their
   elements, a paragraph the sanitizer shortened, a paragraph], read both tables as nowhere, tolerated the shortened
   paragraph and passed, the first table's block owned the tail's paragraphs and the last paragraph was refused as an
   HTML block where d831e7a28 mapped it; the first table's block owns its table and the `<br>` now, the second its own
   table, the shortened paragraph is a mismatch with its own `<p>` and the last paragraph maps; the opener's own
   checkbox kid and an unwrapped `<form>`'s kid are the names); and a block of closing tags with the text the raw puts
   after one of them (`</center> trailing text`, CommonMark's type 6) resumes a swallowed run as a block of closing
   tags alone does (`nextAnchor`'s closer branch keyed on the block's tags, not on `blank`), its one node being that
   text, read past where the DOM holds it at the candidate (`scanTake`), and `runFits` reads such a block past by its
   text inside a run to the end (the branch keyed on `blank` had skipped the block, no later block resumed and every
   tail paragraph was refused as an HTML block at the button's offset, where main mapped them). Two shapes recorded by
   that pass, not fixed, each pinned as an expected refusal so a change shows, and routed to Slice 8 with their
   scenes: one plain paragraph between the `</center>` closer and the two tables is swallowed (the candidate at its
   `<p>` fails at the second table, whose element is not at k past the foster-parented `<br>`, and no later candidate
   is right; main and d831e7a28 map it; the fix is a model of the parser's foster parenting, a `<br>` inside a `<tr>`
   standing as a top-level node before the table); and a removed `<input type="text">` block before a kept checkbox
   block in the tail refuses the tail on every Slice 5 tree (the forward scan meets the checkbox's INPUT; main maps
   it; the fix is `topTags` reading an `<input>` tag's type and marking a non-checkbox input as an element the
   sanitizer drops); and the review's closing pass 3, the final records pass (the termination rule: no fresh-eyes
   finder followed it, and the review is closed on the owner's cap), two fixes and one record, each pinned in
   anchor-map-pairing-r6.test.ts: the texts a repeated paragraph is checked against are the blocks' AFTER the
   swallower, the ones whose nodes can be candidates, not the whole document's (`repeatedFrom`, built per `nextAnchor`
   call over the blocks from b + 1, carried on the `ToEnd` record as `repeated` and read by `runFits`' `unique`, a
   count read in a run to the end alone): the closing pass 2 built its set once over every block, so a copy BEFORE the
   swallower, whose node stands before the resume index and is never a candidate, withheld the html-element
   confirmation, and with a tail that did not line up to the content's end (the removed `<input type="text">` before a
   kept checkbox, the R1b class, or the two raw tables with the foster-parented `<br>`) every candidate failed, the
   resume fell to the first node of the tag from k, a swallowed paragraph's `<p>`, and the tail's paragraphs before
   the html block were refused as an HTML block at the text input's or the html block's offset, their Raw offers
   landing there ([F, INTRO, a `<button>` opener, `Alpha <button>probe</button>`, NOV, LAST, `</details>`, F, TANGO,
   an html `<p align="center"><img>`, A, the removed input, C, the kept checkbox, B]: F's second copy, TANGO and A,
   where f4d803b56, d831e7a28 and 99e7e2d0c mapped them, main refusing them another way; a heading at the top with a
   tail paragraph's text the same, the set keying on text alone; a regression in the safe direction the closing pass 2
   introduced, outside the fuzz9 corpus, so that pass's zero-lost figure below holds on the corpus alone); each maps
   from its own `<p>` now, the html block owns its own picture `<p>`, the button's block owns the run alone, the same
   documents with the top copy removed map as before, and a copy at the top AND inside the run AND in the tail still
   refuses the run's copy at the button's offset and maps the top and tail copies, the run's copy being after the
   swallower; `nextAnchor`'s `bounds` seeds `taken` with the candidate's own nodes, [i, scanTake(nb, i)), the ones the
   resuming block's scan takes from the candidate, so a later same-tag html block whose element is nowhere forward
   does not fail the right candidate at that element (a kept `<input type="checkbox">` block as the resume of a run
   with no closer, [INTRO, `<button>`, `<button>probe xray</button>`, NOV, `<form><input type="checkbox"></form>`,
   LAST, the checkbox, C, a removed `<input type="text">`, B], or with the checkbox as the opener's own kid: the
   removed input's behind scan met the candidate's own INPUT at `from`, every candidate failed and `hit` took the
   first INPUT from k, the unwrapped form's or the kid, inside the swallowed run, so the checkbox block owned that
   input, LAST's `<p>` and its own input, and LAST was refused at the checkbox block's offset, past the passage, its
   Raw offer landing there, a wrong ownership inside a refused region on every Slice 5 tree since round 8; the
   checkbox block owns its own input alone now, the button's block the run with the input inside it, C and B map, and
   LAST, inside the swallow, is refused at the button's offset, its Raw offer landing on the swallower, where main
   maps LAST through its per-block resync); and, recorded, not fixed, pinned as an expected refusal so a change shows
   and routed to Slice 8: two blocks of closing tags with text in a row after a swallowed run (`</center> one text`,
   `</div> two text`) leave their texts in ONE text node, the browser appending consecutive character tokens to the
   same node, so neither block's candidate reads its own text at the candidate (`scanTake` through `pastText` wants
   the node run's text EQUAL to the block's), no later html block resumes and the tail after the swallow is refused as
   an HTML block to the document's end at the button's offset, on every Slice 5 tree, where main maps it (the fix
   shape: a closer-with-text block reading a text node whose text STARTS with its own when the next block's after-text
   follows, or the read split by prefix; one such block alone resumes the run since the closing pass 2). The shapes
   the three closing passes recorded and routed to Slice 8, each pinned so a change shows: the closing pass 2's plain
   paragraph between the `</center>` closer and the two tables (QS2, test 17) and its removed `<input type="text">`
   before the kept checkbox (R1b, test 16), the nested-formatting adoption-agency shape stated in `topTags`' docblock
   (a mismatch refusal as on main, its scene in the closing pass 2's probe, no pin), and the closing pass 3's two
   closer-with-text blocks in a row (test 20); the closing pass's own record, the `place.pic` seat, stands in item
   1b), main's per-block resync at such a block (the review's round 4: with a `</center>` alone as the only later html
   block the swallow had run to the document's end; its round 5: the resume took the first end where TWO blocks lined
   up, so a paragraph after the closer repeating one inside the swallowed run paired to the inner copy, the first
   rendered copy mapped to the last copy's offsets and a comment on the last copy painted on the first, where round
   3's swallow to the end had refused the selection and painted the right copy through the fallback), and no more; an
   html block whose element is nowhere in the content, an unwrapped `<button>` or a dropped `<style>`, is read past to
   the next html block (the review's round 5, fuzz seed 1322's shape: the search ended at such a block, so a
   `<tr><td>` note the parser drops before a `<button>` opener swallowed every paragraph to the document's end)). And
   a selection's end boundary is placed by the last character it selects (`locate`, `descend`), never by the node that
   starts where it ends, so a whole-paragraph selection right before a bare hoisted text node, or a mark a comment
   painted over one, maps (main's rule and round 2's refused it as touching that block while a selection one character
   short mapped). Then the resync runs from there. Where no end lines up and the scan took an element, the scan's
   answer stands and the mismatch that follows is refused with its own node (the stripped-style scene of
   anchor-map-fixtures/blank-scenes.json, the Slice 4 note's item 10 (d): the list item whose source the sanitizer
   shortened is a mismatch with its own element and the paint reaches the closing paragraph); a block whose scan took
   nothing (a dropped `<style>` before a mismatched paragraph) takes every node up to the next html block's own
   element (`nextAnchor`, the review's round 3), where it took every node to the document's end before. Three
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
   and left to the resync: a top-level `<td>` or `<tr>` the parser drops (its text is read past as a bare node), a
   `<p>` left open INSIDE an open wrapper at the raw's END (depth one and more; the top-level case is modelled,
   `pOpen`; one the raw closes by an implied end IS read since the review's round 7, below), a start tag's implied end
   tags in a block's INLINE html (a `<button>` or a `<select>` closing an earlier block's open button or select and
   the `<p>` around it: the swallow is bounded at the next html block's element, or a block of closing tags alone,
   instead, `nextAnchor`; the `<p>`'s button scope itself IS modelled since the review's round 4, `P_SCOPE_BARRIERS`
   in `walkedBlocks`: the blocks after a `<button>` block nested in an open `<p>` nest in the button until its closer,
   which leaves the `<p>` open, and the next paragraph closes it), and a formatting element a paragraph leaves open (a
   `<b>` with no closer), which the parser reconstructs as a top-level wrapper around every later block, so the next
   block takes the whole wrapper as a mismatch and every block after it has no node (pre-existing on main,
   byte-identical there; the fix shape, recorded in the build report's round 3: a `Block.leaves` of the formatting
   tags a paragraph leaves open, and after such a block pairs a following top-level element of that tag spliced and
   added to the block's `wrap`; routed to Slice 8's pairing work by the review's round 4, item 10 (j) and Slice 8's
   brief, section 2 (l)). Also not modelled, recorded by the review's round 8 and routed to Slice 8 with them,
   refusals and not wrong maps: a stray `</p>` the document BEGINS with, for which the parser mints no `<p>` before
   the body opens (`topTags` reads a depth-0 `</p>` as the parser's empty `<p>`, which holds mid-document), so the
   block's scan takes nothing and, with a paragraph the sanitizer shortened before two confirmations, the plain resync
   hands the paragraphs before the next html block's element back only there (fuzz8 seeds 400 and 670; main's
   one-confirmation resync mapped them); the parser's in-select insertion mode, in which a `<td>` or `<p>` start tag
   inside an open `<select>` is dropped and its text kept (fuzz5 seed 117, a different loss pattern on main); the
   plain resync's own cost, one mismatch after one confirmation failing every candidate end and swallowing the
   paragraph before a barrier pair (fuzz8 seeds 348, 607 and 771), where main's resync maps that paragraph and
   swallows everything after the barrier instead, so over the fuzz8 corpus 99e7e2d0c refused 1,907 (seed, paragraph)
   pairs against main's 6,603, and the closing pass's tree fails 1,782 of the 33,987 checks: 1,746 refusals, 36 paints
   of a repeated passage on another rendered copy (main shows 41 such, 99e7e2d0c 48 and d831e7a28 39; seed 1132's, the
   one the closing pass's tree shows and main does not, main fails another way and every Slice 5 tree shows) and no
   wrong-offsets map, where main has 8, 99e7e2d0c 19 and d831e7a28 seed 1330's one; and over fuzz9, fuzz8 with a
   repeated-paragraph family added in 438 of its 1,500 notes (35,082 checks), the closing pass 2's tree fails 2,272:
   1,498 paragraph refusals, 751 foreign refusals and 23 paints of a repeated passage on another rendered copy, every
   one a wrong copy on main too (a `<span/>` or `<div><form>` wrapper whose repeated copy carries the inline closer,
   the paint's text fallback, pre-existing), and no wrong-offsets map; zero wrong mappings new against f4d803b56,
   d831e7a28, 99e7e2d0c or main, no mapping lost against f4d803b56 on the corpus (the one loss found outside it, the
   closing pass 3's top-copy shape above, is fixed) and none lost by that pass against the other three (the 8, 11 and
   69 lost against d831e7a28, 99e7e2d0c and main were lost at f4d803b56 already), and 197 mappings f4d803b56 had lost
   against main map again; on the same corpus f4d803b56 has 77 wrong-offsets maps and 90 wrong copies, d831e7a28 106
   and 120, 99e7e2d0c 103 and 114, and main 6 and 196 over its 34,381 checks (the one-mismatch tolerance for the plain
   path is what ruling 10's wrong-copy guard keeps this slice from adding; the owner's call); a paragraph whose inline
   `<math>` text elements hold text, or whose svg `<title>` or `<desc>` holds an HTML element, or whose
   `<foreignObject>` holds text, which is a mismatch with its own `<p>` (the exact walk emits the text the sanitizer
   drops, the shortened-block class of the Slice 4 note's item 10 (d)), refused for Rendered selection with the Raw
   offer and painted through the fallback, identical on main; and the `<tbody>` the parser inserts between a `<table>`
   and a `<tr>` a raw table omits it from, and the implied end of a cell at the next `<td>`, neither in `topTags`'
   chain (`startTagCloses` has no table-part rule), so a paragraph typed inside an unclosed raw table's cell pairs
   with the TBODY and is refused as a mismatch with the Raw offer (a one-cell one-paragraph table maps only because
   the TBODY's stripped text equals the paragraph's; main refuses the paragraph after the table too; a bounded fix is
   an implied TBODY at a `<tr>` under TABLE and IMPLIED_TABLE_CLOSES in `startTagCloses`, left for the pairing
   follow-up). Within an html block's raw the parser's implied end tags are read since the review's round 7
   (`startTagCloses`: a `<p>` in button scope closes at a block-level start tag through any open inline element, not
   at a `<table>` in the sanitizer's quirks-mode document; an `<li>` at the next `<li>`, a `<dt>` or `<dd>` at the
   next, an `<option>` at the next `<option>` or `<optgroup>`, a heading at a heading, a `<button>` at a `<button>`),
   every element still open above an end tag's element is listed among the kids, each under the one below it, and
   `</form>` on a form nested inside an open element removes the form alone with the rest left open one depth up, the
   parser's rule (round 6's flattening listed only the children closed by their own end tag, so a `<p>` closed at
   `</form>`, `</button>`, `</fieldset>` or `</label>`, or a `<select>`'s end-tag-less `<option>`s, were discarded
   from the kid list, the DOM held them where the depth-1 wrapper was expected and the nested paragraphs were refused
   as mismatches, a regression against 701728eae); a top-level form's end tag closes the form and every element still
   open inside it together, as 78c0806ce did, where the parser removes the form alone and leaves the rest open as a
   wrapper around every later block, so `<form>Lead<b>x</form>` at depth 0 is the unclosed `<b>` above to the parser
   and a closed block to the scanner, and the paragraphs after it are refused (the review's round 8, recorded with the
   unclosed formatting tag above; no behaviour change); and a `/>` on an HTML element is ignored as the parser ignores
   it, so `<div/>` opens a wrapper (round 7; a `<title/>` drops the block's rest and a `<textarea/>` shows it as its
   text, where round 6 read them as leaves; pinned over the real parser since the review's round 8,
   anchor-map-wrappers-browser's round-3 table: the README's `<a name="top"/>` anchor block, a `<div align="center"/>`
   and a `<span/>`, each owning its element with the paragraphs after mapping, red over a git archive of 78c0806ce,
   the node stand-in's parser closing a `/>` at once so the pin is the browser leg's). The round 1 edge of the run
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
   takes the node at k, the first of the holder's spliced children the raw's own kids did not account for, when it is
   that element and a child of the holder, sets k past it after the splice and reads its own raw kids past (before,
   `<div class="in">` after `<div><div>` took the depth-1 wrapper itself and spliced its children a second time, a
   regression against main; the indented `<details><summary>` README shape among the five pinned; the review's round
   5, HIGH, a regression against 50b19bfdb: round 4 had taken the holder's LAST same-tag element child for it, so once
   a later block had closed the inner element and another had nested a same-tag element in the holder,
   `<div align="center">` after `<div><div>`, a nested paragraph and `</div>`, that later element was spliced as the
   depth-1 wrapper and k moved past it, every paragraph between was the opener's and the blocks after paired one node
   late; now the opener's block holds its two wrappers and the later div is its own block's, in the inline-closer,
   details-with-summary-and-div, centred-div and closed `<div>Marker</div>` shapes too). `pastKids` reads a `#text`
   kid as the run of text nodes and highlight marks from k whose text together is the kid's, as `pastHoisted` reads a
   hoisted text by `htext` (since the review's round 5 `TopTag.kids` is a list of `Kid` entries and a `#text` kid
   carries its text, the raw between two real tags as the DOM shows it, `htmlText`'s reading with comments and bare
   `<` inside the run included), two `#text` kids in a row as one run (an html comment splitting the text), a `<mark>`
   the raw itself puts after the text as the next kid's, where the run's text ends, and a run whose text is not the
   kid's ending the read for the resync to decide (before, a Text node alone, so once a comment was painted on a
   wrapper's lead text the same-tag kid after it was taken by the next html block; round 4's run had no bound, so it
   also took the bare nodes the NEXT html block leaves at the wrapper's level, an unwrapped `<option>`'s text or a raw
   `<mark>` block's element, the wrapper's block owned them and the Raw offer for the option's text searched from the
   wrapper's offset, where they are that block's now, the refusal on the option's text carries the option block's
   offset and the Raw search lands on the option's own copy when the lead repeats its words). A highlight `<mark>`
   whose every text node is blank, a control's included, is no node of the pairing's, at the root and in a wrapper's
   splice (`holdsContent`, `blankMark`: the panel paints its pass with the trim deferred, so a comment across a nested
   paragraph and an inline wrapper's opener left a blank mark between the `<p>` and the `<span>`, the span block's
   scan met it where its element was expected, took nothing, and every later block was swallowed until the pass's
   trim, a later comment across the same opener painting its first half alone; a formula-only comment's mark holds the
   formula element alone and stays the formula block's node). And `nextAnchor`'s bound at a block of closing tags
   alone (above). The review's round 5 corrected three of those in place, the depth-1 wrapper's node, `pastKids`'
   bound and `nextAnchor`'s resume, and read `nextAnchor`'s search past an html block whose element the content lacks,
   each above. anchor-map-wrappers.test.ts (38 cases over anchor-map-fixtures/wrappers-plain.md, wrappers-2block.md
   and wrappers-unclosed.md, synthetic, and every scene of blank-scenes.json reaching its closing paragraph, the
   sanitizer's drops stood in for; four from the review's round 1: the pairing across adjacent wrappers, the closing
   tag inside a paragraph, the formula at a selection's end, and the wrapper's per-mark cost as childNodes reads
   counted over 40 nested paragraphs; five from its round 2: a leftover wrapper closed inline on its only paragraph
   before an img, a centred div, a details or plain paragraphs, the regions layer's span read as its picture over a
   README's pictures and an `<img>` then `<div>` block, the unwrapped form and option, the closing-tag block right
   before an inline closer, and the closer inside a blockquote's paragraph or a loose list item with a tight item's
   and a heading's minting nothing; eight from its round 3, the stand-in's parser taught the ignored end tag and the
   button-scope close: `<label>`, `<legend>` and `<option>` closed inline before an html `<p></p>` block, a comment's
   mark over a `<form>`'s lead with every passage mapping after and a partial mark that splits the text, an open `<p>`
   followed by `<br>`, `<img>` and `<span>` blocks and by a table, the same-tag leftover in its div, span and
   `<div><p>Lead</p>` shapes, two closers and one closer after an open `<p>` and a README's centred `<p>` of a
   picture, the whole-paragraph selection by its text node's end and by its element's end before a hoisted text node,
   the summary, lead-text and banner comments counted once against the block's rendering, and the `<button>` opener's
   swallow bounded at the next html block; seven from its round 4, red over a git archive of 50b19bfdb: the display
   formula after an open `<p>` owning its span with the Raw offer at it, a comment painted on a wrapper's lead text
   with every passage after it mapping, a partial comment splitting the lead and an author's `<mark>` after it, the
   stray `</div>` and `</details>` closing an open `<p>` with the `<img>`, `<br>` and table blocks after them owning
   their elements, `<center>`, `<dir>`, `<li>`, `<dd>` and `<dt>` wrappers after an open `<p>` with the `<button>`
   control's nested paragraphs refused as the `<p>`'s HTML block, the depth-1 wrapper before a same-tag block in five
   shapes, two comments across an inline wrapper's opener painted with the trim deferred, and the `<button>` opener
   bounded at a `</center>` alone; four from its round 5, red over a git archive of 701728eae: the depth-1 wrapper
   before a later same-tag element nested in the holder, in the plain, inline-closer, details-with-summary,
   centred-div and closed-marker shapes, the resume after a closer block with `November` and `Last` repeated after it
   and with one repeated paragraph as the document's last block, a comment stored on the second copy painting on the
   second rendered copy, the `<button>` opener after a `<tr><td>` note the parser drops, with a `<div>marker</div>`
   and a `<style>` swallower in the note's place, and the next html block's bare nodes at the wrapper's level after a
   lead text, an unwrapped `<option>` and a `<mark>` block, with the refusal at the option block's offset; test 37's
   `<p>` block scene from its round 6, `<p></p>` and `<p>marker</p>` after the `<tr><td>` note and the `<button>`
   opener's run: the paragraphs after the `<p>` block map, the block owns its own element alone, the run's paragraphs
   are refused at the note's block, whose offset is before the passage, so the Raw offer's search from it lands on the
   passage (the round found the title claiming the scene with no scene pinning it, and the code handing the `<p>`
   block the run's minted `<p></p>`); and test 27 given the two selections that distinguish the trees, the whole
   paragraph ending at the hoisted text node's offset 0 and at the root's child index, red over b1c6cb303 where round
   3's pin had passed), anchor-map-pairing-r6.test.ts (20: four new in the review's round 6, each red over a git
   archive of 8924fa17e: the unwrapped kid leaving an element before the depth-1 wrapper,
   `<div align="center"><button><img></button><div>`, a `<form>`, a `<label>` or a `<fieldset>` holding a `<b>`, a
   `<p>` or a lead text, a `<select>` with two options, a `<textarea>`, a `<button>`'s picture before a
   `<details><summary>`, with the kept-kid, text-only-kid and top-level-form controls, the nested paragraph and the
   one after mapping and the opener's block holding its two wrappers; the html `<p>Final para three.</p>` copy after a
   swallowed run refused as an HTML block with the paragraph after it mapping from its own `<p>` and a comment on it
   painting there, with the distinct-text and `<div>` controls; the `<p></p>` block owning its one element with the
   swallower owning the run and the refusal's offset before the passage, after the `<button>` opener, after a dropped
   `<tr><td>` note and with the intro repeating the passage, with a `<div>marker</div>` control; and the shortened
   paragraph `Weird <style>x{}</style> line.` third, last and fourth of five in the tail after a `</center>` closer,
   the other tail paragraphs mapping and the shortened one refused as a mismatch at its own offset, with a no-closer
   control; and two from its round 7, each red over a git archive of 78c0806ce: test 5, the element the parser closes
   implicitly at an unwrapped element's end tag listed among the kids, a `<p>` closed at `</form>`, `</button>`,
   `</fieldset>` or `</label>`, the finder's `<form>Lead<p>x` shape, a `<form>` holding text, a `<b>` and a `<p>`, a
   `<select>`'s `<option>`s written without end tags, `<optgroup>`s, two controls, and `</form>` with a `<span>` still
   open over a hand DOM, the opener's block holding three wrappers; test 6, the shortened paragraph first and second
   in the tail after a `</center>` closer with the other tail paragraphs mapping and the button's block owning the
   run's four, a two-block tail, the recorded swallow with two shortened paragraphs, and the html `<p>` block's
   candidate confirmed at its own `<p>`, the html copy refused and the markdown copy mapping from its own element,
   with the repeated-paragraph scene, the tail copy mapping to its own offsets; and three from its round 8, each red
   over a git archive of 99e7e2d0c: test 7, the wrapper whose nested blocks are [P1, a paragraph the sanitizer
   shortened, P1 again] with nothing after, each copy mapping to its own offsets, the wrapper's block owning the
   wrapper alone and the shortened paragraph a mismatch with its own `<p>`, for a `<div>` open to the end, a centred
   div closed after the copy, a `<details><summary>`, a div closed right after the copy and a `<span/>`, over the node
   stand-in and a hand DOM, with a paragraph after the copy and no shortened paragraph as controls; test 8, the
   lookahead confirming nothing by an html block's tag alone, a `</center>` resume with a tail [paragraph, html `<p>`,
   paragraph], the README's `<p align="center"><img>` in the html block's place, `nextAnchor`'s html `<p>` candidate
   and a `<div>` control; test 9, the run to the end reading an html block whose element stands behind k as a
   misaligned run, two raw tables with a foster-parented `<br>` between them after a swallowed run over a hand DOM,
   the paragraphs before the tables the leading `</p>` block's as recorded, with a `<p>Lead.</p>` control; and four
   from its closing pass, each red over a git archive of d831e7a28: test 10, seed 1330's shape, the second copy
   mapping from its own `<p>` and the first the button's; test 11, the checkbox block before the swallow and as the
   opener's kid, the tail mapping, with a no-checkbox control; test 12, the div with trailing text after a `</center>`
   resume, before and after a shortened paragraph, with a plain control; test 13, the adoption agency for six
   formatting elements inside a wrapper and one at the top level, with properly nested, no-inner-div and inline-only
   controls; and four from its closing pass 2, each red over a git archive of f4d803b56: test 14, two and three
   paragraphs repeated inside and after the swallow with the html `<p align="center"><img>` after the second copies,
   each second copy mapping from its own `<p>` and a comment on it painting there, the first copies the button's, the
   copies reversed after the closer too, with seed 1330's shape, a plain paragraph in the html block's place, two
   shortened paragraphs after it and two unique paragraphs before it as controls; test 15, the
   `</center> trailing text` closer as the resume and inside the tail, and with an html comment splitting its text,
   the tail mapping and the closer block owning the text node, with a wrapper control; test 16, the kept checkbox
   block inside the tail before a removed text input, every tail paragraph mapping, with the removed input before the
   checkbox recorded as a refusal; test 17, the two tables after the resume, with a checkbox block before the swallow
   too, the first table's block owning its table and the `<br>`, the last paragraph mapping, the opener's checkbox kid
   and an unwrapped `<form>`'s kid as the names, with the plain paragraph before the tables recorded as a refusal; and
   three from its closing pass 3, tests 18 and 19 red over a git archive of 13785194e: test 18, a paragraph at the top
   of the document and again in the tail after the swallow, the html `<p align="center"><img>` after it and then the
   R1b tail or the two tables, the tail copy, the paragraph before the html block and the paragraphs after it each
   mapping from its own `<p>`, the html block owning its picture `<p>` and the button's block the run alone, a heading
   at the top with the tail paragraph's text the same, with the top copy removed, and with three copies, the run's
   refused at the button's offset and the top and tail copies mapping, as controls; test 19, the kept checkbox block
   as the resume of a run with no closer, an unwrapped `<form>`'s checkbox inside the run and the opener's kid, the
   checkbox block owning its own input alone, the button's block the run with the input inside it and the swallowed
   paragraph refused at the button's offset, with a `</center>` closer before the tail as a control; test 20, the two
   closer-with-text blocks in a row, their texts asserted one text node, the tail recorded as a refusal at the
   button's offset) and anchor-map-wrappers-browser.test.ts (6 legs over the real viewer and the real panel,
   real-viewer-leg.ts: the Files pane at 900 and 380 px, the two-block fixture, the chat modal, and, the review's
   round 2, the panel OPEN over a standalone `<img>` block after a lead-text div and after a details, a README's logo,
   screenshot and demo pictures, an `<img>` then `<div>` block and the seeded lead-text div closed inline on its only
   paragraph then an img, every nested passage mapping and the comment served on it painting with a Scroll link; and,
   its round 3, comments served on a details summary, a two-line summary, a centred div's lead text and a README
   banner's tagline and heading painting with marks and Scroll, a comment spanning from the paragraph before a
   `<tr><td>` note into its nested paragraph with the five passages mapping after, the open `<p>` with `<br>`, `<img>`
   and `<span>` blocks and with a table, the same-tag leftover, the stray `</p>` after an open `<p>`, and the
   `<button>` opener with the paragraphs inside its run refused at the button's block and every passage after the next
   html block mapping, and, its round 6, the `<tr><td>` note, `<button>` opener and `<p></p>` block scene, the
   `<p></p>` block owning one P and the note's block the run's four, and a centred div holding a `<button>` around a
   badge picture before its inner `<div>` wrapper, the nested paragraph and the one after mapping and the opener's
   block owning the outer div, the badge and the inner div, and, its round 7, five scenes: a `<form>`, then a
   `<label>`, holding an open `<p>` before the inner `<div>` wrapper, the `<p>` among the kids and both paragraphs
   mapping, a `<select>` with two options written without end tags, a `<form>` closed with a `<span>` still open, the
   opener's block holding three wrappers, and a `<button>` opener's run, a `</center>` alone and a tail whose second
   paragraph the sanitizer shortened, Note, Final and After mapping, November and Last refused, the button owning
   four, and, its round 8, nine notes in the same table, which gained a `last` field for a passage read from its LAST
   rendered copy to the last occurrence's offsets: a centred div closed after a repeated footer line with a shortened
   paragraph between the copies, a details open to the document's end and a `<span/>` block each with a repeated last
   paragraph; the self-closing `<a name="top"/>`, `<div align="center"/>` and `<span/>` blocks owning their element
   with the paragraphs after mapping; a `<button>` opener's run, a `</center>` alone, then a paragraph, an html `<p>`
   block and a paragraph, and the same with a README's centred picture `<p>`; and two raw tables with a
   foster-parented `<br>` between them after a swallowed run, then a shortened paragraph and a last paragraph (the
   repeated-footer and lookahead notes red over a git archive of 99e7e2d0c, the self-closing notes over one of
   78c0806ce); each drag maps to the passage's offsets, offers the float and opens the composer with the quote and
   Save; the anchor-map exports ride a probe bundle injected after the load, so its cache is not the panel's, and the
   panel's own mapping is read through the composer's quote). md-config-paint-trim-browser.test.ts's confinement of
   its rendered-blank oracle to the blocks the paint reached is lifted: every scene reaches its closing paragraph, and
   the fixture's note says so.
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
   way back loses the Raw rows' excess over the summary's box alone, 24 to 60 px, the recorded class, 78 from the
   `</details>` closing a shut fold two deep, five rows of closers and blanks to the block after the wrapper (the
   review's round 6); the cap costs the plain closing row AT the edge 6 px on its round trip, exact before, its
   block's row 36 px down against the summary's 30, and a shut fold's summary 2 to about 8 px below the edge in
   Rendered, the paragraph before the fold out of view, its depth on the Rendered to Raw to Rendered trip, the summary
   pulled to 0.2 px (2 and 5 px measured at 900 and 380; the band is the summary's margin over the block before the
   fold; the review's round 4's record), where the summary at or above the edge is exact; a carried block whose row's
   distance leaves the summary partway above the edge keeps it, so the round trip from a wrapped summary 10 px in
   stays exact where a seat AT the edge from any hidden row would lose the 10 px (the cap, not a seat at the edge from
   every hidden row, is the rule, accepted by the review's round 4; the closed-details node test 4 and browser tests
   4, 7 and 8 pin it); and the round trip from the fold's OWN rows, the opener, the summary, the blank after it, still
   loses the fold's source height, since the way back from the summary at the edge is ruling 13's, the block after the
   fold at its distance with the fold's source above: 402 to 420 px at 900 and 744 to 780 at 380 for a five-paragraph
   fold (round 2's 406 to 413 and 683 to 690 with the landing now right), and the loss has no bound but the fold's
   length (the review's round 6, two probes agreeing, identical at 50b19bfdb and 701728eae): the same fold with
   fifteen paragraphs 1122 to 1140 at 900 and 2202 to 2220 at 380; a fifteen-paragraph fold nested in a second
   `<details>` inside a `<div align="center">` 1248 from the outer `<summary>` row and 1302 from the `<div>` opener's
   at 900, 2328 and 2382 at 380, 1194 and 2274 from the inner summary's, up to four times a 600 px pane's height, the
   `</div>` on top of Raw and the title the reader had on top off the pane. For the fold's own rows that inverts
   main's outcome: main, which refused the wrapper's block and left the numeric scrollTop standing, returned the outer
   summary's, the opener's and the `<div align="center">` opener's row BELOW the edge and in view at both widths in
   every shut-fold scene measured: 52 to 210 px in the refuter's scenes, ten lead paragraphs then a shut fold of five
   or fifteen, top-level or two deep, its Rendered stop (the pre-slice landing, recorded above) having put the summary
   32 to 227 px down with the paragraph before the fold on top at 900 and two deep, Paragraph 9 of the ten at 380
   top-level, and 144 to 562 px in the finder's, a fifteen-paragraph fold after thirty lead paragraphs mid-document or
   ending the document and a five-paragraph fold ending it at 380, its Rendered stop 150 and 524 px down at 900 and
   618 to 636 at 380, off a 600 px pane, with Paragraph 29, 24 or 27 of the thirty on top; the fold's hidden rows both
   trees put above the edge, main by 216 to 414 px and this tree by the rest of the fold's source, 222 to 1950, and
   the closers after an OPEN fold main put 432 to 630 above where this tree keeps them in view (the tail class below).
   The fix shape is `Place.lead`'s carry, below, honoured across a view switch as the picture's is, the `<summary>`
   row put back where the summary was; it touches rulings 2 and 13 and is the owner's call, recorded here and in the
   build report, not built), and a fold the person opened seats the row's own paragraph as before (the review's round
   4: round 3's `shutFoldBefore` had read an OPEN fold's summary, met as the previous shown sibling of the fold's
   first nested block, as a shut fold's, so from the fold's own Raw rows the first nested block was capped at the
   summary, the `<summary>` row's round trip lost 6 px where it had been exact, paragraph 11 at 30 px against its 36,
   and the opener's row put the summary at the edge in place of the row's own distance; a summary whose fold is open
   caps nothing now, paragraph 11 back at 36 with the summary at 6.2, the opener row landing it at 54 and returning
   31 px low, the recorded open-fold class, and the shut fold's summary a stand-in reading rects alone reaches is
   capped as before; the closed-details node test 6 and browser test 9 pin it); a paragraph inside a shut fold whose
   place carries no block after the fold (a place of another making) still seats nothing; a paragraph inside a shut
   fold with NOTHING standing after the fold, the document's last block or only a comment, a wrapper's end or a
   reference definition after it, carries an EMPTY list (`foldStands`, since the review's round 6) and the seat stands
   on the fold's summary at the edge, the cap's own limit (before, such a place carried no list, the seat walked back
   through the hidden paragraphs to the wrapper's refused block and left the numeric scrollTop standing over the
   shorter view, the summary 617 to 636 px down at 380, off the pane, and the way back 505 to 729 px low; the pane's
   end mostly clamps the summary's write, the summary lands near the pane's bottom, and a clamped seat holds the Raw
   place in file-view.ts, so the way back returns the row exactly; file-view-place-last-fold-browser.test.ts, 1 leg,
   new in round 6 and red over a git archive of 8924fa17e: at 380 and 900, a fold ending the document, one followed by
   a comment alone and one by a reference definition alone, from the `<summary>` row, the `<details>` row and a hidden
   paragraph's row, the switch writes scrollTop, the summary is at the edge or the body at its end with the summary in
   view, and the way back returns the row within 1.5 px, a fold with paragraphs after it the control; the
   closed-details node test 4's hidden-only and empty-list cases seat the summary at the edge).
   file-view-place-blocks.test.ts (14; the two wrapper tests rewritten, the stand-in's wrapper children given boxes
   stacked inside the wrapper; built with the stand-in on the shim ratchet's allowlist, unswitched, then switched by
   the merge of main 6aef10815, which brought fork PR #569: FakeNode, FakeText and FakeElement end their constructors
   in hideEdges, main's projection case is the fourteenth, the ratchet's allowlist is empty with ALLOWLIST_MAX at 0,
   and 40a4db43a asserts the file's non-empty node lists through sameNodes, by identity; the merge's hand resolve kept
   the rewritten test 10 with main's one sameNodes assertion carried onto its equivalent line),
   file-view-place-html-browser.test.ts (16; test 16 from the PR review's round 1, the Raw read's whole-block parse
   counted through DOMParser across twelve scroll frames over a 300-row table, once per block per source; test 13
   re-pinned in the review's round 7, the `<p align="center">` row holding the logo and the project's name from the
   picture 48 px in standing at the `<p>`'s fraction, not the
   picture's, and from Raw the `<p>` at its box, red over a git archive of 78c0806ce; tests 3 and 4 exact round trips
   as before: the picture after a `<details>` back at its depth within the Raw row's whole-pixel snap scaled by the
   picture's height over the row's, about 5 px at 900 px; the rule scene moved 2 px below the edge, since
   `.fileview-md hr` is a 1 px hairline whose bottom at 0 sits on the very bound topVisibleIndex reads and the
   browser's sub-pixel snap then decides which block is the place; test 3's summary row switched to Rendered puts the
   fold's summary at the edge (round 3; round 2: the block after the shut fold where its row was, 100 px down); and
   from the review's round 2 a fold title at the top edge, open and shut, at 900 and 380 px, exact, with the closing
   row followed by a comment, and a README's centred header from Rendered and from each of the wrapper's rows; and,
   its round 3, the wrapper's own picture, a logo and a 900x600 banner, at 900 and 380: from the picture's top to
   300 px in, the picture back within the row's whole-pixel snap scaled by the picture's height over the row's, test
   3's bound (4.5 px for the banner at 900, under 2 px for the other three; the review's round 4 measured 3 px for the
   banner 300 px in at 900 and 0 to 1 px in every other scene), and from its Raw tag row at the edge and 9 px above
   it, the picture at the row's fraction within the same bound, 0.5 px measured, and the row back within 1.5 px, and,
   since round 7, a seat into Raw with the edge inside a picture leaves the picture's row two pixels below the edge at
   least (`ROW_SHOWN`): the fraction asked for less at a tall picture's foot, with the edge in the last ten pixels of
   the 508 px banner over its 72 px row the row's bottom rounded to one pixel, the read passed the row for the blank
   after it, the nested heading was seated at that row's distance, and the banner came back 12 to 20 px higher, wholly
   above the edge; clamped, the row is read and the banner returns within two row pixels scaled by its height over the
   row's, its foot in view (picture-line test 5, the banner's bottom 8.5 and 5.5 px below the edge at 900, red over
   78c0806ce; at 380 within the snap scaled, as before, and two bands of the same class stand beside the clamp,
   recorded in round 8 and not fixed: with the picture's bottom from about the nested heading's gap less the blank row
   above the edge to the snap pixel below it (the 508 px banner's from 9.5 px above to 0.5 below at 900) the Rendered
   read carries the heading at its distance, 19 to 29 px, the Raw seat leaves the tag row's tail 1 to 11 px under the
   edge above the blank, the read back takes the tag row, right for a Raw reader with that tail in view, and the way
   back returns the banner 23 to 77 px lower, 9 to 18 for the logo, identical on 78c0806ce and 8924fa17e (main refused
   the rows, 324 px); a cap on the heading's Raw distance at the tag row's bottom at the edge, the shut-fold cap's
   shape, would trade the banner's 77 for the heading's 10 and waits on the owner's word; and a TOP-LEVEL tall picture
   (an `<a href><img></a>` block or a `![banner]()` paragraph outside any wrapper) carries no Place.pic and keeps
   Slice 2's fraction seat unclamped, so with its foot 1.5 to 5.5 px below the edge at 900 its row's bottom rounds to
   one pixel, the read passes it and the banner returns wholly above the edge, 11 to 15 px higher, identical on main
   213fde5fa (Slice 2's seat and Slice 3's threshold, outside this slice's items), recorded for the owner); and, its
   round 4, test 10: from the `<div align="center">` opener row and the blank before it, the logo and the banner at
   900 and 380, the picture at its row's distance below the edge and the row back in view; test 8's `<img src=` row
   scene at both widths; and, its round 5, tests 11 to 15 at 900 and 380, each red over a git archive of 701728eae:
   the run's ten rows, a comment's before the opener with and without a blank line and the blanks beside it, the
   `</div>` closing a wrapper before a second one and the blank after it, a shut fold's `</details>` before the
   opener, and the outer opener of a wrapper two deep with the blanks beside it, the picture where its tag row was and
   the row back in view; the logo at the edge and 30 px in and 10 px into the badges from Rendered, and the way back
   from the badges' row; the `<p align="center">` holding a picture and the project's name from both views; the
   wrapping fold title across a drag and back, the aside and A+; and the commented-out `<img` tag paired with no
   picture), file-view-place-wrapper-end-browser.test.ts (3; tests 1 and 2 exact: nested paragraph 60 in a centred div
   closed last, never closed and `<details open>` closed at the end lands on its own Raw row and returns within
   1.5 px, and its Raw row 3 px above the edge seats its own `<p>` at the row's depth scaled),
   file-view-place-edits-browser.test.ts (4; test 1 tightened to exact, paragraph 80's own row and back at the same
   height), file-view-place-closed-details.test.ts (16, the review's rounds 1 to 7 and the PR review's round 1, whose
   test 16 counts the Raw read's lex and parse of an html block across scroll frames, once per block per source: a
   stand-in whose elements answer checkVisibility as Chromium does and one without the API; the read; the seat's
   refusal for a place carrying no
   block after the fold; the Raw read of closers, comments, the wrapper's rows and the carried blocks, a chain of two
   folds included; the seat standing on a carried block, capped at the summary since round 3; and, round 3, the
   wrapper's own picture read and seated at its fraction; and, round 4, an open fold's summary capping nothing where a
   stand-in's shut fold's summary still caps, the Raw read carrying the picture from a row before its tag row, the
   Rendered read carrying a picture below a lead `<h1>` the edge is inside, and the Raw row at the edge kept across a
   reflow; and, round 5, the Raw carry through the run in five shapes, every row named and the shut fold's cap, the
   picture at the edge among badges and a logo both ways, a picture in a row with text, Place.lead across a summary
   grown from 40 to 80 px, shut and open, at 0 and 10 px, with a Raw seat and other text leaving it unused, and the
   commented-out tag; and, round 6, test 4's hidden-only and empty-list cases seating the summary at the edge and test
   11's way back from the badges' row reading the line's union; and, round 7, test 12 re-pinned to the `<p>`'s box
   both ways, the caption case seated and inverted exactly and the parts seat over a grown caption, and test 13, the
   stand-in's `<p>` with the picture under the caption keeping the row's rule, and the seat into Raw leaving the row
   at 2 px with the read back taking it, at 0.42 px passing it, both red over a git archive of 78c0806ce) and
   file-view-place-closed-details-browser.test.ts (10 legs over the real viewer: the round trip at 900 and 380 px; the
   closing row from Raw for a shut and an open fold; the hidden row seating the block after the fold and the opened
   fold seating its own paragraph; the wrapped summary's exact round trip at both widths; the two-closer block from
   either row; comment rows inside a wrapper; and, the review's round 3, the long fold's rows and the sibling `</div>`
   rows at 900 and 380 with the summary at the edge, and the closing-row round trips with a comment, a reference
   definition, the blanks beside the closer and the wrapper's `</div>`; and, its round 4, the open fold's `<summary>`
   row round-tripping exactly with the first nested block at its own distance, and eight Raw rows held within 0.4 px
   across A+, A- and a pane drag at 900 and 380). The edge inside a wrapper's own lead picture (a README's banner or
   logo in a centred div, a linked logo, a badge row), or a row of the block's own at the edge with the picture below
   it, is the one row of a wrapper's block the seat stands on in both directions (the review's round 3, widened in its
   round 4 and corrected in its round 5; `Place.pic`, the picture's tag line and its box: readRendered carries the
   picture AT the edge among the block's own rows' pictures, from the level's first box on, the one the edge is inside
   whose top is nearest it, else the topmost below it, so the picture the edge is inside or the first one below the
   edge under a lead `<h1>` the edge is inside (`atEdge`; not the first in document order: pictures of different
   heights on one line share a baseline, so a line of small badges before a tall logo has its tops 96 px below the
   logo's while it comes first in the DOM, and round 4's first-in-DOM carry took the badges' line with the edge at the
   logo's top, the Raw seat put the badges' row 96 px down and the logo's 276, and the round trip lost 129 to 440 px;
   and not the deepest, since from the badges' own row Rendered puts the badges at the edge with the logo above it and
   the way back must read the badges again, which the shallowest-inside rule does: the logo's top at the edge
   round-trips exactly at 900 and 380, and the badges' row within the picture's snap scaled by the row's height, 4 px
   at 380 for a 342 px data-URI row over a 24 px picture; and, since round 6, the pictures whose tags share ONE source
   line are one box to both reads, their union, `pictureLines`, `linePictures` and `lineBoxes` (`picBox` until round
   7), since one Raw row cannot tell them apart and the union is the one box it inverts: read one by one, the edge
   105 px into a logo with a 24 px badge beside it on the line carried the badge, the picture the edge was inside
   whose top was nearest, the Raw seat put the shared row at the badge's fraction and the way back took the line's
   first tag, the logo, at that fraction, 60 to 62 px lost, 12 to 13 for two badges of 48 and 24 px and 56 with the
   badge first, where 701728eae's first-in-DOM carry had named one picture both ways; the pick AMONG lines is
   unchanged, so badges and a logo on two lines read as before; file-view-place-picture-line-browser.test.ts test 2 at
   900 and 380 pins the shared row at the line's fraction and the tracked picture back within the row's snap scaled,
   and the closed-details node test 11's way back from the badges' row reads the line's union over the stand-in's
   stacked badges), every `<img>` of a row counting whether or not the row holds text of the note's (`picturesOf` over
   `ownRows`, the one definition for both reads; round 5: the Rendered read had refused a row with text, so
   `<p align="center"><img><br><b>Name</b></p>` was a picture to the Raw read alone and the round trip with the
   picture at the edge lost 64 px at 900, 40 % in 82, exact now both ways at 900 and 380; and since round 7 the box
   such a row's one Raw row inverts is the ROW's, the `<p>` with the picture and the name, not the pictures' union
   (`rowOfLine`, `lineBoxes`; `Pic.imgs` keeps the pictures' own box beside it): read from the name under the picture,
   the Rendered read had carried no picture, the union ending above the edge, and seated the nested heading at its
   distance, the Raw read carried the `<p>`'s line as the picture's, and the way back put the union at the row's
   fraction, 32 and 71 px lost at 900 (the logo and a badge over the name; a linked logo over the name), 20 and 51 at
   380, 64 and 59 from a tagline 150 px into the `<p>`; both trips are exact within the row's snap scaled by the
   `<p>`'s height over the row's now, and from the picture 48 px in the `<p>`'s row stands at the `<p>`'s fraction,
   not the picture's (the html leg's test 13 and the closed-details node test 12 re-pinned so;
   file-view-place-picture-line-browser.test.ts test 4 at 900 and 380, red over a git archive of 78c0806ce)), a
   commented-out `<img` tag counting for none (`IMG_TAG` skips html comments, `DETAILS_TAG`'s idiom; round 5: it
   paired the k-th picture with the tag before its own and put the comment's row where the picture was, 18 px off),
   the walk ending at the first nested block or wrapper; readPlace's Raw branch carries the first `<img` line of the
   first block holding one in the RUN from the top row's block to the block before the one the row reads as, at or
   after the row in the top row's block and anywhere in a later one: the tag row itself, the `<div align="center">`
   opener, an `<h1>` lead row, the blank before the opener and, since round 5, a comment's row or a closer's before
   the opener, the `</details>` of a shut fold or the `</div>` of a wrapper closed right before it, the outer opener
   of a wrapper two deep and the blanks beside them, with that line's own row, and asks `opensWrapper` no second time,
   every block of the run reading as the block after it and only one that opens a wrapper able to hold a tag (round 5,
   HIGH, a regression against main identical at 50b19bfdb and 701728eae: round 4 read the row's own block alone, so
   from those rows the picture landed above the edge, the logo 4 to 22 px and the banner 60 to 410, and the row
   returned 44 to 94 px above the edge, off the pane, where main kept it in view; now the picture lands where its tag
   row was, 36, 54 or 72 px below the edge by the row's distance, and the row returns 41 to 59 px low, the
   paragraph-before-the-wrapper tail class); and the seat puts the picture, or the row, at the same fraction of its
   height when the edge is inside it, the rule a top-level picture has had since Slice 2 and the html leg's test 3
   pins, and at the same distance below the edge otherwise, as any block that starts below the edge keeps its own,
   and, for a picture read from Raw through a SHUT fold's closing row and the rows after it, no lower than the fold's
   summary at the edge, the cap every block read so keeps (`shutFoldBefore`; round 5: uncapped, the
   `</details>`-before-the-opener scene put the picture at its row's distance, left the paragraph before the fold's
   tail 24 px under the edge, and the way back brought the fold's five Raw rows back between, the closer 127 to 128 px
   low at 900 and 380; capped, the summary is at the edge, the picture under it, and the row returns above the edge by
   the three Raw rows' excess over the summary's box, about 32 px, the recorded closing-row class); the picture is
   found from the tag's index among the block's `<img` tags outside comments, `picturesOf`, `pictureLines`, `imgLine`,
   `imgIndexBefore`, `linePictures`, `rowOfLine`, `lineBoxes` and `lineBoxesAt` (the line's pictures' union since
   round 6, or since round 7 the box of the row holding them beside text of the note's; `picBox` until then), and a
   picture the view does not show leaves the seat to the rules below). Round 4's correction (HIGH, against main: a
   wrapper's own row BEFORE its lead picture's tag row read as the first nested block at its row's distance, so the
   switch to Rendered put that block there and the picture, 120 to 508 px tall against one Raw row, above the edge,
   the logo's top at -40.5 and the banner's at -428.5 at 900, and the way back seated the tag row at the picture's
   fraction, the opener's row 32 to 109 px above the edge and off the pane, where main had kept it in view 38 to 45 px
   low): from the opener row and the blank before it the picture lands at its row's distance, 18 and 36 px, and the
   row returns in view 23 to 27 px low at 900 and 380 (the paragraph before the wrapper's tail by its fraction, the
   recorded class); the `<h1>`-and-banner README's opener, blank and `<h1>` rows round-trip exactly (65 to 109 px off
   before); the picture's top 2 px below the edge round-trips exactly (59 to 447 px off before); and the `<h1>` 10 px
   in round-trips exactly at 900 and 380 (the review's round 5 re-measured the scene, which round 4's record had as
   26 px low; what returns low is the `<h1>` 2 px below the edge with the banner under it, 24 px at both widths, and a
   lead taller in Rendered than its Raw rows, an `<h1>`, two `<p>` and the banner, 50 to 54 px: the way back seats the
   paragraph before the wrapper by its fraction, the recorded class below, where 50b19bfdb read 0 at 900 only because
   its Raw write clamped at the document's top and lost 137 to 155 px at 380, and main 126). The closed-details node
   tests 7 and 8 and the html leg's test 10 pin it. One residual of the same class, recorded and not fixed (the
   review's round 5): the logo's top 2 px below the edge with a tall badge row above it, three data-URI badges on the
   line before the logo, a Raw row of 180 px at 900 and 342 at 380, returns 122 px high at both widths on the Rendered
   to Raw to Rendered trip (701728eae: 63 at 900 and 135 at 380), the badges' row's 2 px tail above the logo's row
   being the top Raw row on the way back, read by its fraction as a paragraph's tail is; the two Raw rows share one
   Rendered line box, so no per-picture rule inverts it, and the logo AT the edge is exact and pinned. The residual's
   second face, from RAW (the review's round 6, recorded and not fixed): the same header with a row of the wrapper's
   block BEFORE the badge line at the edge, the opener, the `<h1>` or the blank before the opener, comes back 245 to
   454 px high on the Raw to Rendered to Raw trip: the Raw carry names the badge line at its row's distance, Rendered
   puts the badges there with the logo, 96 px taller on the same baseline, reaching above the edge, and the way back
   reads the logo, the picture the edge is inside, whose row the Raw seat puts at that fraction; that Rendered
   geometry is the one a reader 60 to 78 px into the logo makes from Rendered, whose own trip must read the logo to
   invert (the html leg's test 12 and the closed-details node test 11 pin the logo pick), so no rule of the Rendered
   view alone tells the two scenes apart (701728eae's first-in-DOM carry inverted these rows by accident while losing
   the logo's own trips, 129 to 440 px). The one stateless rule that inverts every scene, the recorded 122 included,
   is a wider unit, the pictures of CONSECUTIVE tag lines as one box in both reads, the union in Rendered and the run
   of their tag rows in Raw; it changes which Raw row tops the view from the logo at the edge (the badge line's, not
   the logo's, which the html leg's test 12 pins) and waits on the owner's word; holding a seated place across every
   view switch until the reader scrolls is the wider change still. Not pinned: the plan records residuals without
   pinning known-wrong numbers. The owner's round-3 ruling asked for the picture's top at the edge both ways, the same
   rule at the top level; the fraction was kept instead, since the top level's fraction round-trips exactly and the
   header states it, and the picture's top alone would lose the reader's depth (150 to 300 px into a banner) and
   regress the from-Raw scenes with the tag row partway above the edge; the review's round 4 accepted the fraction as
   the rule, pinned by the html leg's test 9 and the closed-details node test 5. Before: read as the first nested
   block below the picture, whose row the Raw seat put where the block was, the paragraph before the wrapper topped
   the Raw view whenever the picture's height above the edge exceeded the wrapper's rows and the way back was its
   fraction seat, 36 px for a logo's top at the edge at 900, 430 to 442 for a banner 50 to 300 px in, 70 to 82 for the
   banner at 380, and 40 in reverse from a data: URI row wrapping to 144 px at 380 (html leg tests 8 and 9,
   closed-details node test 5). And the way back from rows that render nothing on top of Raw (a closing-tag row after
   an OPEN fold, a reference definition, a comment, a `<div align="center">` opener row) loses their Raw height's
   excess over the Rendered box between the previous block's tail and the block after them, by that tail's fraction
   seat: 38 to 78 px for an open fold's closer, 41 to 43 from a `<div align="center">` opener row, 96 to 121 after a
   display formula inside a wrapper (three Raw rows, one 18 px line rendered), 78 to 96 from the opener row of a shut
   fold whose text sits in its html block, 60 to 78 from its summary row, 42 to 60 from its text row (900 to 380), 86
   to 111 from the rows of a fold two deep opened, `<details open>` inside `<details open>` inside a
   `<div align="center">`, the outer `<summary>` 96 to 97, the inner fold's `</details>` 98 to 111 and the `<div>`
   opener 86 to 98, and 83 at 380 from the `<table>` row of a wrapper's own eight-row table, each `<tr>` row wrapping
   to two Raw lines there, exact at 900 where they do not (the review's round 6, identical at 701728eae, where
   50b19bfdb had put the open fold's outer summary and `<div>` opener rows 60 and 114 px above the edge; main returned
   them 72 to 144 px low, the fold's closer 432 to 630 above the edge and the finder's eight-row table's row 116 low,
   210 for the refuter's shorter table at 380 and 56 at 900), against 9 for a plain blank row: the fraction seat of
   the partway block is the design's rule, and the residual grows with the rows. A reflow of the same RENDERED text
   with a shown row of a wrapper's block's own at the top edge keeps that row where it was since the review's round 5
   (`Place.lead`, the picture's mechanism widened to every shown row of a wrapper's block for a same-view reflow,
   built on the coordinator's ruling: readRendered carries the row of the block's own at the edge, by `atEdge` from
   the level's first box on, as the wrapper block's span, the row's ordinal among the block's own rows less its
   wrappers, `ownRows`, and its box; seatPlaceOutcome, for a Rendered seat over the same source in the same view,
   before the picture's rule, puts that row back at its distance below the edge or at its fraction of its height when
   the edge is inside it, `seatedTop`, the picture's rule, unless the edge is inside the place's picture or the row
   holds one of its line's pictures and the view shows them, when the picture's rule stands (`picOutranksRow`, the
   review's round 6: an inline `<a>` around a logo has its font's box, 18 px at the picture's bottom, so seated by the
   row a linked logo, `<a href><img></a>`, the common README header, fell 2.1 px per text-size step and 4.3 over two,
   and the `<p>` around a logo and the project's name drifted 1.9 to 2.9 by the `<p>`'s fraction, where 701728eae's
   picture rule alone had held both within 0.1; a row holding no picture of the line, a summary or a lead `<h1>` over
   a banner, keeps the row's rule; so, since round 7, does a row whose own text stands ABOVE its picture with the edge
   in that text, `<p align="center"><b>Project</b><br><img></p>` (round 6's clause took the picture's rule for any row
   holding one of the line's pictures, so the logo below the edge was held and the name at the edge rose 2.9 px per
   text-size step, 6.9 with two lines of words over the logo, where 8924fa17e's row rule had held it within 1.3;
   picture-line test 3 at 900 and 380 and the closed-details node test 13, red over 78c0806ce); and a row that holds
   its picture on a line of its own beside text over or under it is seated by its PARTS (`rowPartsTop`): the edge
   inside the picture keeps the picture's fraction; the picture's top AT the edge, within the snap pixel and a seat's
   half-pixel landing below it (`PIC_AT_EDGE`, 1.5 px, shared with `picOutranksRow`; round 8: classified exactly, the
   text-first `<p>` whose logo's top a whole-pixel scroll landed 0.3 to 0.9 px below the edge took the row's fraction
   on one step and the picture's on the next and drifted the logo 2.6 to 3 px per text-size step, 2 px off after A+,
   A+, A-, A-, where 78c0806ce held it within 0.5; picture-line test 6 at 900 and 380, red over 99e7e2d0c), goes back
   at the whole pixel nearest where it stood, the edge or the pixel above or below it, the same ask on every reflow,
   and the band reaches the same distance above the edge, into the picture's first pixel, so that the fixed ask's
   landings stay under it (the review's closing pass: round 8 asked for the top where it landed, and the landings,
   each within half a pixel of its ask, walked one way at 700 to 800 px, 0.91, 1.27, 1.75 over A+, A+, past the band,
   so the first A- took the row's fraction, 2.5 px, and the four steps ended 2 px off, where 380 and 900 had bounced
   within half a pixel of the start; with the band below the edge alone the fixed ask's landing 0.2 px inside the
   picture at 300 px handed the top to the picture's fraction, which walked it 1.01 px from the start; test 6 runs 700
   too, red over d831e7a28, and the round-8 recheck's harness holds the logo within 0.65 px at 300, 380, 500, 600,
   700, 800, 900 and 1100, floor and ceil landings, the four steps ending where they began; the picture's own seat in
   the `place.pic` branch, a picture that is a row itself or a lead row over a banner, still asks for the top where it
   landed, so its landings can walk the same way: a linked logo's rule flips at no top, and a lead `<h1>` over a
   banner whose top stands within the band below the edge could take the row's rule through `picOutranksRow` after
   such a walk, unmeasured, recorded here and left, with the two bands beside the clamp, for the owner); in the text
   under it its distance from the picture's bottom scaled by the row's line-height, the one style the module reads
   (round 7 had the part's own fraction, which held the name within 1 px across a text-size step, where the `<p>`'s
   fraction had moved it 2.3 to 8.7 px per step and the picture held 1.5 the other way by the strut's growth, but took
   the tagline's wrapped lines for growth on a pane drag and moved the name 3.6 to 4.6 px and the tagline's line 9.6
   to 12.6 between 900 and 380; a drag leaves the line-height as it was, so both hold since round 8; picture-line
   tests 4 and 8, test 8 red over 99e7e2d0c), and in the text above it the row's fraction (the text part's own
   fraction moved the name by its depth times the line's growth, 1.9 and 2.7 over two steps; with the edge in a second
   line of words over the logo the row's fraction moves the `<p>` 3.2 to 3.7 px up and the words at the edge 4.1 to
   4.6 down over two steps, round 8, measured and recorded; the exact seat there, the line's own top, is not read for
   Rendered text, the Slice 3 review's decision); and a row whose pictures stand BESIDE its text on one line, a 24 px
   icon before a README's `<h1>` name, keeps the row's rule whatever part the edge is in (`picInLine`, by the row's
   line-height: the pictures no taller than a line, or the row less than a line taller than they are; round 8: the
   parts model took the edge inside the icon for the picture's part, held the icon and let the heading's text rise by
   the line's growth, 4.5 px per step at 380 and 3.7 at 900, or took the row's rule as the sub-pixel landing fell; the
   row's fraction holds the text's cap tops at the edge within half a pixel per step with the edge 5 px into the
   heading and within 2 px with it 8 px in (1.1 at 900 and 1.7 at 380 over two steps, the pin's bound), and the icon
   falls with its baseline, 2.5 to 3.8 per step and 5.3 to 7.3 over two (measured; round 8's note had half a pixel and
   3.3 to 3.5, corrected in the closing pass), the one refuter's point that no seat holds both being right;
   picture-line test 7 at 900 and 380, red over 99e7e2d0c); file-view-place-picture-line-browser.test.ts test 1, new
   in round 6 and red over a git archive of 8924fa17e, holds the linked logo at the edge, 48 and 100 px in, and the
   `<p>` row 48 px in within 1 px across A+, A+, A-, A- at 900, and the linked logo across a drag 900, 380, 900 and
   the Comments aside); a view switch or other text leaves it unused, and the row is still never the place, so rulings
   2 and 13 stand). Round 4 had recorded the drift for a text-size step alone, 4.5 to 4.9 px above the edge per step,
   compounding (-4.7, -9.3, -15.3 over three steps at 900), the kept block, the block after a shut fold or the first
   nested one, keeping its distance while the summary's own growth landed above the edge, and left the fix to the
   owner as touching rulings 2 and 13; round 5 measured the same mechanism at a pane drag with a wrapping fold title,
   shut and open, 67 to 90 px above the edge from 900 to 380 and 147 to 190 down after the drag back, and 23 px above
   it when the Comments aside opened, where main held every one within 0.2 px. Now, over the real pane with a title
   67.3 px tall at 900 and 134.5 at 380: the drag to 380 with the title at the edge exact, 10 px in at its fraction,
   the drag back exact, 380 to 900 and back exact, the aside opening and closing exact, A+ then A- exact, and a lead
   `<h1>` with the banner under it across A+ exact (was 7.6 px off). The closed-details node test 13 and the html
   leg's test 14 pin it. In RAW the rows hold since the review's round 4: a reflow of the same Raw text (a text-size
   step, the pane dragged, the Comments aside opening or closing) keeps the top ROW (`Place.row`, the row at the edge
   when the kept block starts at or below it, its span and its top, set by readPlace's Raw branch; seatPlaceOutcome,
   for a seat in Raw over the same source, puts that row back where it was, before every other rule), so the
   `<summary>` row, a comment's, a closer's, a wrapper's opener, the blank before a fold's opener, the blank after a
   closer, a blank between paragraphs, a reference definition's row and a logo README's opener hold within 0.4 px
   across A+, A- and a pane drag at 900 and 380 (before, a row read as the block after it rose 2.7 px for each row
   between them, 5 to 11 px per step, where main, which read each such row as its own block, held them within half a
   pixel: the `<summary>` row 4.9 to 5.4, the blank before a shut fold's opener 10.8, the logo README's opener 15.9 at
   900 and 47.1 at 380; a plain blank row rose 3 px on main and here alike, and holds now); a paragraph's own row is
   unchanged (`Place.line`). The closed-details node test 9 and browser test 10 pin it. The Slice 2 note above records
   refusals (1) and (2) as history now.
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
   reference outside `NAMED_ENTITIES` is the browser's own reading where a DOM is to hand, the webview (since the
   review's round 5, `domRefText`: a `<textarea>`'s innerHTML set to the reference and its text read back, memoized
   per reference, the decoder probed once with `&amp;&ltimes;` so a stand-in that keeps the markup or knows no HTML5
   name is never taken for it, and the parser's longest-head reading recovered from the decoded tail, so `&check;` and
   `&ltimes;` show their glyphs, `&notxyz;` the not sign and `xyz;`, `&semi;` a semicolon, and `&nosuchname;` stays as
   written), and keeps its source form where none is, the node tests under the shim (the table is the fast path and
   stands in there: since the review's round 4 HTML 4.01's 252 names with HTML5's code points, `apos` and the
   upper-case aliases `AMP`, `COPY`, `GT`, `LT`, `QUOT` and `REG`, so an HTML5-only name such as `&check;` is what
   stays there, and since round 5 the 39 HTML5 names headed by a legacy name, `ltimes`, `parallel`, `notni`,
   `centerdot`, kept as written too, `HTML5_LEGACY_HEADED`, where round 4's legacy-prefix rule had read `&ltimes;` as
   `<imes;` and `&parallel;` as the pilcrow and `llel;`; round 3's table held six names, so `&mdash;`, `&copy;` and
   `&hellip;` in a README's html blocks and cells never matched the glyph the DOM shows and a comment on such a
   passage painted nothing; the table is an object with no prototype read through an own-property test since round 5,
   where read with `in` it had answered Object.prototype's functions for `&toString;`, `&constructor;`, `&valueOf;`
   and `&hasOwnProperty;`, whose source text skewed every position after the reference in its paragraph and vanished
   from an html block's needle, while the DOM shows such a reference as written); in an html block, whose raw marked
   passes through, the 106 legacy names and a numeric reference decode with no semicolon as the parser decodes them,
   `charRefAt` and `decodeHtmlText`, an unknown name taking its longest legacy prefix, `&notit;` the not sign and
   `it;`, while in a paragraph marked's escape keeps a semicolon-less reference literal; a numeric reference follows
   the parser's end state, `numericRefText`: U+FFFD for zero, a surrogate and a code past U+10FFFF, the windows-1252
   character for a C1 control, and one map entry per code unit, so an astral character's quote keeps its last
   character; a `<pre>` inside an html block keeps the newline after its start tag; a `<template>`'s content, a
   fragment the DOM never shows, is dropped; and, from the review's round 5, a body `<title>` is dropped with its
   content, a block, one inside a `<div>`, inline in a paragraph or in a cell (`TITLE` in `DROPPED_CONTENT`, as the
   sanitizer now drops it, item 10: round 4 had read a `<title>` block the document begins with as its text and
   recorded the departure, since the parser puts that one in the head, and had an inline `<title>` show marked's HTML
   for its tokens on the claim that the sanitizer unwraps it, where DOMPurify's svg profile KEPT a body title as an
   element the UA sheet hides, so nothing of it showed while its text stood in the DOM, in the hay and in the reader's
   text, and a comment on it painted a mark with no box whose card offered Scroll to nothing; both are closed by the
   drop on both sides), an svg's `<title>` kept (`dropsContent`: `TITLE` is dropped in HTML content alone); an RCDATA
   element left open across blocks (`<textarea>`, `<plaintext>`) is read to its block's end where the parser reads on
   (history since decision 52 of plans/file-review.md, 2026-09-18, for the start tag written in prose with no end tag
   in its block, which is literal text on both sides now, md-literal-tags.ts; the divergence is left to a `<textarea/>`
   or a `<plaintext/>` written with the self-closing syntax, which the parser opens);
   an inline `<textarea>` shows marked's HTML for the tokens inside it, decoded (`Parser.parseInline`:
   `<b>b</b> <em>c</em>` for `<b>b</b> *c*`, where round 3 read the tokens as markup), rendered as the viewer rendered
   THIS document, the file kind's token walk run over the tokens first (`fileKindWalk`, since round 5:
   file-view-links.ts's viewerWalkTokens, then any walk on marked's defaults, through marked.walkTokens so an
   extension's child tokens are reached, so a wikilink inside the textarea is the anchor the DOM shows and a
   same-directory link target the viewer's form, where the reader's own lex had rendered the dead span, class and
   title and all, and the needle matched nothing); inside an `<svg>` or a `<math>` the raw-text rule is off
   (`FOREIGN`), so an svg's `<title>` is an ordinary element closed by its own end tag or the svg's (round 3 read
   `<svg><title>inner title</svg> beside` as the title's text to the block's end), in the inline read too since round
   5 (a stack of open foreign roots, `ForeignRoot`, shared with `lenientHtml` through `closeForeign`: the root's end
   tag closes every element opened inside it, `</svg>` a `<foreignObject>` and the drop stack with it, unless an HTML
   element stands open inside the foreignObject, when the parser ignores the end tag, the foreignObject's own too, and
   the block's rest stays inside the dropped foreignObject (`ForeignRoot.open`, round 6:
   `<svg><foreignObject><b>x</svg> y` read `Intro y` against a DOM showing `Intro`; the parser swallows the later
   blocks too, which no tree models, recorded; round 7: every integration point of the root is read so
   (`ForeignRoot.ip`, `integrationPoint`: MathML's mi, mo, mn, ms and mtext, an annotation-xml with the text/html or
   application/xhtml+xml encoding, an svg's title and desc, inside which an HTML element is also the sanitizer's
   namespace check's to remove with its text), where round 6 modelled the foreignObject alone and
   `<math><annotation-xml encoding="text/html"><b>x</math> y2` read ` y2` against a DOM showing nothing of it; and
   inside the integration point the parser's implied end tags are read (`openInIntegrationPoint`, `startTagCloses`),
   so `<p>a<p>b</p></foreignObject></svg> y` shows ` y` as the DOM does; round 8: `<mglyph>` and `<malignmark>` inside
   a MathML text element stay foreign, as the parser's dispatcher keeps them, so `</mi>`, `</mtext>` and `</math>`
   close and `ma9 <math><mi><mglyph/></mi></math> y9` reads `ma9 y9` as the DOM shows (round 7 recorded them as HTML
   elements left open and dropped the block's rest, where 78c0806ce read on), and the annotation-xml's encoding is an
   exact match of the value, as the parser compares it, so a blank inside the quotes makes it no integration point and
   the reader closes the math at its end tag and reads on, `ma8 y8` against a DOM showing `ma8 x y8`, the breakout
   class as recorded (round 7 allowed the blanks and dropped the block's rest; history since decision 52 of
   plans/file-review.md, 2026-09-18: the `<b>` with no end tag in its block is literal text inside the dropped math on
   both sides, so the DOM shows `ma8 y8` as the reader does, and anchor-map-html-text-browser.test.ts holds the shape
   as an agreement, its recorded divergences the `/>` forms alone); a start tag that breaks out of foreign
   content, a `<b>` inside `<math><mrow>` or an annotation-xml with no HTML encoding, is not modelled, pre-existing
   and identical on main, recorded); round 4's inline branch had no such stack, so `<svg><title>icon</svg> beside` in
   a paragraph, a list item, a quote, a heading or a cell read the title's text to the block's end, tags and all); and
   a raw html table's cell boundary reads a blank, the one `hayRuns` puts between two adjacent table parts
   (`TABLE_PARTS`), so a quote across `</td><td>` matches where it read the cells run together, and only there
   (`nextIsTablePart`, since round 5: the raw going on with another part's start tag past whitespace and comments,
   and, since round 6, past whatever leaves the DOM's parts adjacent, a `<style>` or a `<script>` with its content, an
   empty `<form>`, a hidden `<input>`, and any element the parser foster-parents before the table, `<br>`, `<img>`, an
   empty `<span>`, an `<a name>` anchor, not a `<template>`, kept in the row, and not text of the row's, and, since
   round 7, past a dropped element's TEXT as well, a `<noscript>`, a `<math>` or an svg's `<foreignObject>` between
   two cells, removed whole (round 6 read such an element to its `>` and its text ended the look), with a blank where
   a part's START tag closes an open part implicitly, `IMPLIED_TABLE_CLOSES` and `lenientHtml`'s table frames,
   `<td>a<td>b`, `<td>b<tr><td>c`, a caption closed by a cell (round 7, on every tree: the blank was put at a part's
   end tag alone, so such a table read its cells run together and a comment across two of them painted nothing), and,
   since round 8, `lenientHtml`'s frames seeded with the tables the html blocks before leave open (`renderedBlocks`
   reads the wrapper chain off the tag scans as `walkedBlocks` does: an html block's open tags push, its stray end
   tags pop to their element, a paragraph's honoured closer the same), since marked splits a raw table at a blank line
   into html blocks while the parser keeps the one table open, so a block starting `<tr><td>b1<td>b2` reads `b1 b2`
   where round 7's frames, the block's own, read `b1b2` against a hay `b1 b2` and a comment across those cells painted
   nothing (a `<tr><td>` block with no table open, or after the table's end tag, still reads run together, the
   parser's stray; html-rules test 14 and an html-text-browser shape, red over a git archive of 99e7e2d0c), and a
   raw-text or dropped element written `/>` opening as the parser opens it, `leafTag`, a `<title/>` dropping the
   block's rest and a `<textarea/>` showing it as its text, where round 6 read them as leaves (the parser reads on
   past the block, the recorded class); the round-5 rechecks' residuals: a `<style>` or an empty `<form>` between two
   cells of a minified raw table read the cells run together against a hay with the blank, and a quote across them
   painted nothing; round 4 put the blank at EVERY part's end tag, so text after a table's last part,
   `</td></tr></table>tail`, which the DOM runs on from the cell, read a blank the hay lacked, and a quote from a cell
   across the table's end into it, painted at 50b19bfdb, matched nothing; the recheck's three shapes, the tail after a
   bare table, a nested minified table and a stray `<td>`, paint again). `stripMarkupMapped(s)` is the rendered text
   of `s` read as a document of its own (`buildSourceTable`, beside the cached `sourceTable`), and
   `renderedQuote(source, range)` is exported for the corpus test. The hole reasons are constants (CODE_HOLE,
   INDENTED_CODE_HOLE, TABLE_HOLE), their strings unchanged. The list inherited from the strip at the build is closed:
   a code line opening with three backticks inside a longer fence has been code since the review's round 1 read the
   fence lines by offset, the `*` pairing across two cells and the `\|` inside a code span in a cell since round 2
   read a row cell by cell, and a code line beginning `>` inside a QUOTED fence since round 3, the container's markers
   coming off through the walk's suffix view (the quote-marker rule had taken the line's own `>`); so are the
   constructs round 2 left, the rule of 3 and punctuation flanking, html entities, the shortcut reference link and the
   bracketed label, which the pipeline reads as marked does (a formula inside a cell stays routed to Slice 8, item 10
   (j)). A range spanning prose and a hole is placed by the exact path from its positioned characters, the hole at the
   edge unpainted (item 10 (b) below), so the mixed-kind needle matters only for a range with no positioned character,
   where both sides agree line by line. anchor-map-fallback-markup.test.ts (25; six new, main's projection case, which
   the merge of main 6aef10815 appended after them, two from the review's round 1: a code span's content in a cell and
   a quote begun inside a fence line, with the strip's case list extended, and four from its round 2: same-delimiter
   nested emphasis in a cell, the code span with an escaped pipe and the backslash parity of a delimiter, the escapes
   with the inline tag, the mark, the wikilink, the strong-then-underscore and the cell's trailing backslash, and the
   fallback widening to the whole text when the range's blocks are paired to nodes that do not hold the quote; test
   1's case list extended again, and test 6's count-guard scene, an html block whose attribute repeated its text,
   re-aimed at an entity spelling the text, since the strip now drops a tag with its attributes as the rendering does;
   anchor-map-change-marks.test.ts test 6's scene the same; and from its round 3: test 1 rewritten against the
   stand-in's rendering, test 6 re-aimed, the entity in an html block now painting by ordinal and a refused block
   whose node shows the passage twice staying unpainted over the whole text too, test 16's parity assertion on the
   unmatched backticks the cells show, and five new: the 300-cell seeded corpus as cells and as refused paragraphs,
   each read as the rendering shows it and painted whole, the 110 hand cases of rounds 1 to 3, the prose shapes a cell
   cannot hold, hard breaks, soft-break constructs and the code span's backslash, the cut ranges, `bold words** more`,
   `2024. It was`, `# of items`, the `3. ` continuation and a cut escape, and the html blocks, `costs \$5 raw`,
   `C:\Temp\</div>` and a `<script>` inside; the corpus fails over b1c6cb303 on 488 of its 600 checks and the hand
   cases on 185 of 220; and from its round 4 the verdict's pin, `corpusVerdict`: the failure message counts failing
   checks against twice the cell count, each half against the cells and the distinct failing cells, where it had
   counted both halves against the cells alone, 300 of 300 with the prose half alone failing;
   anchor-map-change-marks.test.ts test 6 moved its count-disagreement scene to a rendering that gained a copy of the
   passage and pins the entity scene as painting the second shown `note`), anchor-map-html-text.test.ts (7, new in the
   review's round 4, each red over a git archive of 50b19bfdb: the minified raw table across cells and rows, the
   spaced table and a table inside a dropped script; block and inline `<foreignObject>` dropped with svg `<text>` and
   `<desc>` kept; the named references, the aliases, the legacy forms in a block and their literal reading in a
   paragraph, the case-sensitive table; the numeric reference quirks with the map's length equal to the text's; the
   inline `<textarea>` in a paragraph and a cell, an inline `<title>`, the block form and the open textarea; and the
   svg `<title>` in foreign content with a style inside an svg dropped; test 6's inline-title pin re-aimed to the drop
   in its round 5), anchor-map-html-rules.test.ts (15: six new in the review's round 5, each red over a git archive of
   701728eae's module: the raw table's blank only between two adjacent parts, with the recheck's three shapes and
   every part kind, the reference table read through an own-property test, the legacy rule kept off the legacy-headed
   HTML5 names where no DOM decodes them, the foreign rule in the inline read in a paragraph, a list item, a quote, a
   heading and a cell, the body `<title>` dropped in four places with the leading-title record closed, and the
   textarea's wikilink rendered with the file kind's walk; and two from its round 6, red over a git archive of
   8924fa17e: the blank between two table parts past a `<style>` holding `<td>` in its text, a `<script>` between two
   tbodies, a `<br>` between two rows, an empty `<form>`, a hidden `<input>`, an `<a name>` anchor and the other
   between-cell shapes, with the template, text, two-tables, tail, comment and unclosed-style controls, and the
   element left open inside a `<foreignObject>` at `</svg>` in a paragraph, an html block and a list item, a second
   open element, `</i>` and `</foreignObject>` ignored, with the closed-element, `fo</svg>`, `<br>`, nested-svg and
   `<g>` controls; and five from its round 7, each red over a git archive of 78c0806ce: test 9, the raw table's
   implied end tags, `<td>ri1 a<td>ri2 b<tr><td>ri3 c`, the README's `<td>Flag<td>Meaning`, th and tbody, a caption
   both ways, one blank not two, a nested table and the written forms as controls; test 10, a dropped element's text
   between two cells, seven fillers with the round-6 controls and the svg title's kept text pinned as recorded; test
   11, the self-closing raw-text tag, `<title/>`, `<textarea/>` and `<noscript/>` opening; test 12, the element the
   parser closes implicitly inside a `<foreignObject>`, thirteen closing shapes and six left-open controls; test 13,
   the integration points, an annotation-xml in four encodings, mtext, mi, mo, the html block, an svg title and desc
   open and closed, with controls; and two from its round 8, each red over a git archive of 99e7e2d0c: test 14, the
   raw table marked splits into html blocks at a blank line reading the implied end's blank against the parts the
   earlier block left open, in a second and a third block and a `<tbody>` block after a `<thead>` block, a `<tr><td>`
   block with no table open or after the table's end tag still run together as the DOM shows; test 15, `<mglyph>` and
   `<malignmark>` inside `<mi>` and `<mtext>` staying foreign, self-closed, as a start tag alone and between text,
   inline and in an html block, and the encoding's exact match with a blank inside the quotes reading on past the
   math), anchor-map-html-text-browser.test.ts (1 leg, 85 subtests, new in the review's round 5: every html-text shape
   rendered through marked, applyMdConfig and sanitizeMd in headless Chromium, the reader's text against the box's
   textContent and each quote's real paintRendered marks over that DOM, the plan's recorded open-textarea divergence
   pinned on both sides (history since decision 52 of plans/file-review.md, 2026-09-18: the open `<textarea>` is literal
   text on both sides and one of the module's agreed shapes, its recorded divergences the `/>` forms alone); red over
   a git archive of 701728eae on the eight round-5 shapes, and 9 of 59 red under a
   sanitizer mutation that kept foreignObject and dropped every title while the text test stayed green, the gap the
   leg closes; its round 6: three round-5 entries' `shown` strings carried a blank the rule removed and passed under
   the marks' whitespace-blind compare, so each `shown` is the text test's string now and the needle compare is
   whitespace-normalized rather than blind, and three shapes from the round's rules, a `<style>` and a `<br>` between
   two cells and the element left open inside a foreignObject, red over a git archive of 8924fa17e; its round 7:
   sixteen shapes and two recorded entries from the round's rules, the raw table's implied end tags with the cells
   asserted, a `<noscript>`, a `<math>` and an svg's `<foreignObject>` between two cells painting two marks, the `/>`
   textarea in an html block and the `/>` noscript, the `<title/>` and `<textarea/>` paragraph forms recorded on both
   sides, three implied-end shapes inside a foreignObject painting ` y`, and the integration points, an annotation-xml
   open and closed, mtext, an svg title open and closed, 17 red over a git archive of 78c0806ce; its round 8: three
   shapes, the raw table whose rows marked splits into two html blocks with the cells asserted, an mglyph self-closed
   inside an mi and a malignmark start tag inside an mtext, and one recorded entry, an annotation-xml whose encoding
   carries a trailing blank inside the quotes, the reader's `ma8 y8` against the DOM's `ma8 x y8` (history since
   decision 52 of plans/file-review.md, 2026-09-18: an agreed shape now, `ma8 y8` on both sides), each red over a git
   archive of 99e7e2d0c), anchor-map-dom-rules-browser.test.ts (1 leg, new in the review's round 5, over the real
   viewer and panel: one `<title>` left in the DOM and it the svg's, the titles' text gone from the viewer and from
   the chat's sanitizeMd, a comment inside a title painting nothing with its card offering Reveal and one across it
   painting the text beside it alone, `&ltimes;` and `&notxyz;` read and painted as the glyphs the DOM shows, and the
   comment on a textarea's wikilink content painting with Scroll; red over 701728eae),
   anchor-map-code-table-paint-browser.test.ts (4 legs over the real viewer and panel: a Raw drag over each passage
   saved through the float and the composer, the posted anchors the exact slices, then the switch to Rendered painting
   the code line whole inside the fence's first row and one mark in each of the row's two cells, each card offering
   Scroll and not Reveal; the same comments served before a fresh open, on the pane and in the chat modal; and, the
   review's round 2, Raw comments on the round 2 cells, the nested emphasis, the code span with an escaped pipe, the
   escaped asterisks, `costs \$5`, the underscore beside a strong, an inline tag's text and a cell ending in a
   backslash, served before a fresh open and painting as the cells show them, every mark in its cell and each card
   offering Scroll; and, its round 3, 39 Raw comments on the round 3 shapes served before a fresh open, each painted
   with Scroll, `_snake_case_` among them, which round 2 had painted with 0 marks and no Scroll). The store's side:
   tools/file-comments-host-anchors.test.mjs (2 guards) and tests/test_file_comments_e2e.py (2 cases) pin that
   uniqueAnchor, locateExact and the comment verb, over the kernel wire, keep the slice with its operator or its
   delimiter and stamp anchorAt; the host was byte-exact before the slice, so both say they are guards.
5. *Item 3, the Raw offer at a formula, and refusals in the person's terms* (rulings 7 and 9). The math holes and the
   formula refusal landed with Slice 4 (its note, item 2), but `formulaExtra` took the Raw range from the selected
   RENDERED text, and KaTeX's glyphs are not in the source: Switch to Raw preselected the prose the drag ran into
   (`math and`) or nothing for a formula selected alone. Now, when the formula's hole is found, the offer is the
   hole's span with its delimiters, `$E = mc^2$` or the `$$` block through its closing line (the line feeds a display
   block's raw carries after it, and any indent before it, trimmed; since the Slice 8 review's round 2 the display
   hole itself ends at the closing `$$` and the indent alone is trimmed: the Slice 8 note, item 5), rawHasQuote true
   and rawRange on blockStartOffset's line: equal to it for an inline formula or an unindented block, and past the
   indent for a display block written with one to three spaces before its `$$` or `\[`, where blockStartOffset stays
   at the hole's raw start, the indent, as before the slice (the review round 1 corrected this note, which had
   recorded the two as equal, and pinned the indented shape); rawTarget (file-comments.ts) searches for the slice from
   blockStartOffset forward, so the switch preselects the formula either way and the composer quotes it with Save;
   where the hole is not found (a hand-typed `.katex` placeholder before the real formula makes the count disagree; a
   formula under no block) the offer falls back to the selected text's occurrence as before, pinned. Six message sites
   carried a token type (`a ${t.type} the mapping could not place` in the inline walk, the block walk and the token
   placement, `${t.type} marks the mapping could not place`, and two defaults with `(${t.type})`).
   `refusalNoun(type, inline)` gives each token its noun: the Slice 4 constructs by what they show (a footnote
   definition, a footnote reference, a display formula, a formula, the front matter, a callout, a highlight for
   `mark`, a wikilink), marked's built-ins with their article (a paragraph, a heading, a list, a list item, a table, a
   code block, a quote, a rule, blank lines, a link definition, text, an escaped character, an inline code span,
   emphasis, strong emphasis, a strikethrough, a link, an image, a line break), `html` as an HTML block or, inline, an
   HTML tag, and "content" for a kind the map has no name for; the sites read `${noun} the mapping could not place`
   and `${noun} whose marks the mapping could not place`, and the defaults are the constant "content of a kind the
   mapping does not handle" with no type. No input the lexer accepts today reaches those sites (every token raw tiles
   the source; fifty odd shapes probed produce only refusals in the person's terms), so the closure is held by the
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
   file-comments-hint-order.test.ts (4 at the slice's end, 9 since the PR review's round 1, below: three copies a
   thousand characters apart with two positionless comments on the first and second, one positioned on the third
   unaffected, a fourth with no copy left back on the first, a unique anchor plain; the hint scoped to an equal
   anchor; the probe's back-to-back line with a two-character context; the words for each copy on the mark's title,
   the tag's title and the open card's line, the review's round 1). The branch's second merge of the fork's main
   (213fde5fa, 2026-09-11) put the host's confirmed copy before both: paintAll's hint is now the copy the host's
   tie-break confirmed (`placedAt`, the file-review plan's decision 51), else the stored position, else the sequential
   hint, and the words for a guessed copy name the confirmed place first, then the hinted copy, then the first copy,
   then the copy nearest the stored position (`hintedCopy` rides on the card as `confirmedAt` does, stamped by
   renderCard and by paintAll for the mark's title; the four pins moved again with it). The PR review's round 1 found
   the executed pins unable to fail on that order (the positioned card sat on the copy the hint would have named
   anyway, and no executed case put a confirmed copy in a pass with a positionless same-anchor card), so
   file-comments-hint-order.test.ts gained five cases in which each pair disagrees, every one reading the copy off the
   Raw rows: a stored position on a copy the hint would not pick wins over the hint, and the positionless card after
   it takes the copy after the positioned one's; the host's confirmed copy wins over a stale position nearest another
   copy, and over both the position and the hint; a confirmed copy in one pass with a positionless same-anchor card,
   in both orders, counts as the previous card's copy for the hint and keeps its own against it.
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
   for ends that match, handing it to onSelection; the review's round 1; history since 2026-09-20, the paint-gap fix of
   upstream/2026-09-20-paint-gap-reoffer.md: a pass reads the selection at its head, before its writes, against the
   selection the last delivered selectionchange found and the one the previous pass left, and a change of the person's
   whose event is still to come leaves the record dropped and the float to that event, the mechanics in the offeredFor,
   lastDelivered, passLeft, pendingChange and afterPaint docblocks of ui/webview/file-comments.ts); a collapsed selection, or one with an end
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
   standing beside nothing; a float beside a selection cut short but not to nothing answers to the test the scroll's
   listener reads (`subjectHeld`, one method since the review's round 6: the remnant has a box and its top and right
   edges sit within a pixel of the offer's, `floatSubjectRect` against `floatAt`, one getBoundingClientRect per paint
   pass while a passage's float shows, a second for a subject that moved and stayed whole, and none otherwise): it
   stays where it was offered while the remnant sits under the button (a cut that trims the selection inside the line
   box the button sits beside), and goes once the remnant has no box or has moved a pixel or more. No box (the
   review's round 5): a selection from inside a paragraph's whole-text mark into the next block's start is cut to a
   bare line break between the two blocks when the rewrap moves an anchor inside the mark's text to the paragraph's
   end, a removed node's descendant boundary points moving to its parent, while the focus at the next block's start
   stays, a range in the body and not collapsed but with no client rect, text nobody can see, which the offer itself
   refuses and whose Comment button opened a composer the whitespace refusal closed at once. Moved (the review's round
   6): the same drag carried into the next paragraph's middle leaves the line break and that paragraph's first half, a
   remnant with a box a line or more below the offer's, and the float stayed where the drag offered it, 74 px above
   the passage it now offered to comment on in the review's scene, a narrower text column than the browser leg's 900
   by 700 px pane, where the same drag measures 52, while a scroll that moves the passage one pixel from under the
   button hides it; low, no regression against main, which keeps the float after any cut, and a rule the round aligned
   with the scroll's rather than recorded); moved WHOLE (the review's round 7): a peer's mark landing through the poll
   on the selection's own line, before it, on it or inside it, wears the sheet's 2 px side padding, so the
   still-selected text stood 4 px further right with no character cut and the remnant's test hid the offer while the
   passage stood selected and visible (8924fa17e and main kept it, 4 px off); afterPaint now tells a selection moved
   whole from a remnant as the seam tells a selection its reflow paint left standing (file-view.ts
   fireRenderedKeepingSelection: both ends in the body and the same text selected, read against the record as the last
   paint left it; not the ends by node identity, which the wrap's split of the text node renames, so an ends test
   reads an intact selection as cut) and offers the float again at the selection's box now, re-recording floatAt so
   the scroll's test measures from the new place; a remnant goes as round 6 rules; a different non-collapsed selection
   inside the body shows the float at its rect. Round 8, two edges of that re-seat: a float the writes find HIDDEN is
   left so, whatever hid it (the picture overlay's press had hid the float through the hidden bit alone and kept
   floatAt, the record afterPaint took for a showing float, so a peer's mark landing on the still-selected line while
   the person pressed on a picture, or after a click on a region's rectangle had opened its card, showed the passage's
   Comment button again beside a selection the press had dismissed; the press goes through hideFloat now, one
   mechanism for a hidden float with its record cleared, and afterPaint guards on the hidden bit as the scroll's
   listener does; low, the slice's own round-7 re-seat introduced it, no regression against main, and round 6 stayed
   hidden only because its afterPaint could only hide); and a passage the writes moved whole OUT OF THE BODY'S BOX is
   no re-seat (`inBodyBox`, a box at least partly inside the body's on both axes: the body clips what it scrolls and
   showFloat clamps to the window alone, so a paint that pushed a last-visible-line selection below the body's bottom
   edge, Show changes inline toggled from the keyboard with a deletion's struck label above the line growing the text,
   seated the button 30 px above a passage nobody could see, over the body's last visible line and the other text it
   holds, the passage at 264.1 to 282.1 px against a body bottom of 262.8 at 500 by 400; 78c0806ce hid it, as for any
   move; the re-seat hides otherwise, as for a remnant that moved, and onSelection's guards are untouched, a gesture's
   selection being in view by the browser's doing). Recorded by the same round, pre-existing and identical on main
   213fde5fa, for the seam's owner: a click on a panel control while a scrolled-off selection stands re-offers Comment
   at the pane's top edge (the mousedown hides the float, the mouseup runs the seam's onSelect with the still-standing
   selection, whose rect is above the pane, and showFloat's window clamp puts the button at 8 px; file-view.ts
   onSelect's control gate covers the title bar's controls alone and onSelection has no body-box test, which every
   shim suite's zero-box body would fail; the seam's gate widened to the aside's controls, or a body-box test in
   onSelection with the shim bodies given a box first, is the route). The quote-chip seed stays on mouseup and
   touchend; the seam comment at file-view.ts onSelection says where the keyboard's path lives. In Chromium a keyboard
   selection needs an existing selection or caret browsing (F7), so the gain is the float following a
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
   offsets, offered again), file-comments-paint-offer.test.ts (9; three from the review's round 1: the float across a
   paint that cuts a live selection, a WeakRef over the offer's text node collected after a reload, and one toString a
   change; one from its round 2: a paint that collapses a live selection to nothing with no selectionchange hides the
   float, the next change offers, a selection cut short keeps it and a hidden float stays hidden; one from its round
   5: a settings-signal paint that leaves a live selection of one line break, not collapsed, in the body and with no
   box, hides the float, the next change offers, a remnant with a box keeps it and a hidden float stays hidden; one
   from its round 6: a settings-signal paint that cuts a live selection to a remnant with a box moved 74 px down and
   55 px in hides the float, the paint's own event re-offers nothing, the next change offers, a remnant within a pixel
   keeps it, one moved a pixel loses it, and a hidden float stays hidden; one from its round 7: a settings-signal
   paint that moves a live selection whole 4 px right, its node replaced and its text the same, re-seats the float
   beside the new box, the paint's own event re-offers nothing, a scroll from the new place keeps it and a pixel's
   move hides it, a whole move by a line follows, a remnant cut and moved still goes, and a hidden float stays hidden;
   and two from its round 8, each red over a git archive of 99e7e2d0c: test 8, a float hidden with its place record
   kept and a paint whose writes move the still-selected passage whole, the float staying hidden and keeping its
   place, the paint's event and a scroll re-offering nothing, the next change offering; test 9, a paint whose writes
   move the selection whole past the body's box, the stand-in's body wearing a box, hiding for a box below the clip
   and for one above it, re-seating for one straddling the edge, the paint's event re-offering nothing and a hidden
   float staying hidden) and file-comments-paint-offer-browser.test.ts (7 legs over the real pane: a peer's comment
   through the real poll cuts a real drag's selection, the hidden float stays hidden and a shown one stays put, and
   Shift+ArrowRight offers; and, the review's round 2, a comment over the whole of a paragraph, a real drag inside its
   mark and a peer's comment through the poll collapsing the selection with 0 selectionchange events, the count
   asserted since the review's round 3 (a browser firing one for the collapse would hide the float through the
   listener's rule and the leg would pass without reaching afterPaint's), the float hidden, then a fresh drag and
   Shift+ArrowRight offering at the widened selection's rect; and, its round 5, a comment over the whole of a
   paragraph, a real drag from its last eight characters into the next paragraph's first character and a peer's
   comment through the real poll, the remnant asserted as one or more line breaks anchored on the `<p>`, not
   collapsed, both ends in the body and with no box, then the float hidden, no composer, and a fresh drag offering
   again; and, its round 6, a comment over the whole of a paragraph, a real drag from its character 20 to the next
   paragraph's character 60 and a peer's comment through the real poll, the remnant asserted as the line break and
   that paragraph's first sixty characters, not collapsed, both ends in the body, with a box a pixel or more below the
   offer's, the float hidden where it stood, no composer, and a fresh drag offering again; and, its round 7, a real
   drag over a plain paragraph's words and a peer's comment landing through the real poll on the same line, its mark
   before the selection, on it or inside it, the selection's right edge moved 4 px with every character still
   selected, the float re-seated beside the new box at showFloat's arithmetic, a scroll event that moved nothing
   keeping it, then Shift+ArrowRight offering at the grown selection and a scroll that moves the passage hiding it,
   with a mark after the selection on its line as the control, the float standing where the offer put it; leg 5 red
   over a git archive of 78c0806ce; and, its round 8, leg 6, a passage's float hidden by a real press on a picture's
   overlay, a click on a standing region's rectangle that opens its card and a press that begins a region drag, held
   while the peer's mark lands through the real poll and moves the passage 4 px, the float staying hidden at its old
   place, the next Shift+ArrowRight offering and the drag's release opening the region composer with the float hidden;
   leg 7, the Files pane at 500 by 400 px, a tracked note with a deletion above the sixth paragraph, Show changes
   inline off, a real drag over that paragraph's words, a scroll making its line the last visible one,
   Shift+ArrowRight, then the inline toggle focused and pressed with Space, the passage moving whole to 264.1 to
   282.1 px under a body bottom of 262.8 and the float going, then, scrolled back, the next keyboard change offering
   inside the body's band; both red over a git archive of 99e7e2d0c). Round 5 found four of the panel's node tests
   reading the selection through per-test fakes that asserted their world's nodes at call time, or pinning paintAll's
   shape: file-comments-about-review2 and file-comments-markclick-controls read their fake once, and
   file-comments-regions, file-comments-reveal-landing and file-comments-behavior pin the pass with afterPaint in it;
   file-comments-regions's pin on the region overlay's press reads `onPress: () => this.hideFloat(),` since the
   review's round 8, the hidden-bit form refused.
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
   and the text around it is kept. From its round 5 a second change in the sanitizer, on the same hook: a body
   `<title>` is dropped WITH its content (`dropBodyTitle`, md-sanitize.ts: the hook moves an HTML-namespace `title` out
   of the tree itself, into a fresh fragment of its document, right before DOMPurify judges it, its one text node going
   with it, so that DOMPurify's own removal of the title under a profile that disallows it detaches from a parent that
   has it (3.4.10's `_forceRemove` throws for a parentless node, which the node's own `remove()`, the round 1 cut, had
   left it as; the PR review's round 2), and leaves an svg's `title` alone; the first cut set `allowedTags.title` false
   for the element and back on for an svg's, and the PR review's round 1 found that set to be DOMPurify's LIVE per-call
   ALLOWED_TAGS, `_sanitizeElements` passing the variable itself, so the write stood on every later element of the
   call, and under `setConfig`, the one mode that keeps a set across calls, would have reached the next call; the hook
   now writes nothing there; the browser shows a title nowhere outside the page's head, and DOMPurify's svg profile had
   kept a body one as an element the UA sheet hides, so its text stood in the DOM, in the paint's hay and in the
   reader's text, and a comment on it painted a mark with no box whose card offered Scroll to nothing), viewer and chat
   alike; item 4's reader drops it on its side (`TITLE` in `DROPPED_CONTENT`, an svg's kept); md-sanitize.test.ts (16:
   the unit test over fake nodes in both namespaces, the hook test reading both bodies, the header; 17 since the PR
   review's round 1: the two bodies read the removal and the set untouched, and the fakes go through the shim's
   hideEdges, the hook's stubs with them, with a projection test; 18 since its round 2: the every-profile test,
   3.4.10's `_forceRemove` transcribed over a title the hook moved, under the html profile alone and under FORBID_TAGS
   with `title`, no throw and the title gone with its text), md-sanitize-body-title-browser.test.ts (2, the PR review's
   round 1, over the vendored DOMPurify in Chromium: `title` true in the set at every element of a call behind a body
   title, the drop without a throw of a title whose text reads as markup, and two calls with one config, as an argument
   and under `setConfig`, the second inheriting nothing; 3 since its round 2: the html profile alone and FORBID_TAGS
   with `title` over the real DOMPurify, no throw, the title gone with its text), anchor-map-dom-rules-browser.test.ts
   (1 leg, new, item 4) and docs/guide.md's HTML paragraph gains a second sentence, an HTML `<title>` is dropped with
   its text, since a browser shows one nowhere outside the page's head, and the `<title>` of an inline `svg`, the
   drawing's tooltip, stays (the svg clause from the review's round 6, which found the sentence had said every
   `<title>` is dropped while the same paragraph says an inline `svg` is kept), with its pin in md-sanitize.test.ts
   over both halves. From its round 6 one change outside the slice's
   units, in the shared Copy button, pre-existing on main: the execCommand fallback of a fence's Copy (code-block.ts
   `fallbackCopy`, the path an insecure origin, a denied permission or a refused Clipboard write takes) moved the
   document's selection into its textarea and left it collapsed outside the passage, and the focus on the body, with
   no selectionchange the document hears, so a passage's Comment button stood beside a selection that was gone and a
   click on it opened nothing (the review's fuzz: 27 steps in 5,040 on main, 3 on the slice's tree), and Space on a
   focused Copy button lost the keyboard's place; the fallback now keeps the selection's two ends, anchor and focus,
   before the textarea takes the selection and puts them back after with setBaseAndExtent, direction kept, and gives
   the focus back to the element that held it, as the Clipboard API path leaves both (round 7: put back as a cloned
   Range, which has no direction, a passage selected right to left came back forward, anchor and focus swapped, so the
   panel, which knows the selection it offered Comment beside by its ends, offered again, at the pane's top edge
   beside nothing when a scroll had taken the passage off the pane and hidden the button, and the next Shift+ArrowLeft
   shrank the selection from the other end; the cloned Ranges stay the route for an engine without setBaseAndExtent, a
   selection of several ranges and a put-back the engine refuses); code-block-copy-keeps-selection.test.ts (7, new)
   over a stand-in whose selection carries a direction bit and file-comments-copy-fallback-browser.test.ts (2 legs,
   new) over the real Files pane, whose origin carries no Clipboard API; file-view-place.test.ts's hideFloatOnScroll
   pin moved with `subjectHeld`. The ledger entry is upstream/2026-09-10-markdown-viewer-slice5.md (tier feature).
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
   and item 4's one pass changes neither (one obstacle in those spans; history since Slice 8, whose items 1 and 2 map
   the cell and the line and whose item 3 refuses the two-cell selection with the Raw view preselecting the span: the
   Slice 8 note); (j) routed to Slice 8 from the review's round 2, no code here: a formula inside a table cell gets no
   Raw preselect, since the table is one TABLE_HOLE whose cells the walk never enters, so the offer is item 3's
   recorded fallback, the selected text's occurrence, and a drag from the formula into the next cell preselects that
   cell's text; and a Raw comment on such a cell paints nothing, the hay dropping the formula element as a control
   while the needle keeps its TeX (item 2); both fall out of Slice 8's exact cell mapping (its brief's section 2 (k));
   and, from its round 4, the formatting element a paragraph leaves open (item 1's not-modelled list, with its
   `Block.leaves` fix shape) to Slice 8's pairing work (the brief's section
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
   changes no box the trim or the margin layout reads; the Raw read asks whether the top row's block reads as the
   block after it once per block per source, not once per scroll frame (the PR review's round 1, fork PR #749; the
   review's round 2 had asked on every frame): readPlace runs once per scroll frame in Raw (file-view.ts notePlace,
   one read per animation frame) and runs `readsAsNext` on the top row's block, on each block of a run after it and on
   each block after a fold the place carries (`foldStands`); `readsAsNext` keeps its answer per block for the last
   source read, as `foldDepths` keeps the fold table, the answer being a function of the block's text alone, and fills
   it on the first ask with `closesAlone` and `isCommentBlock`, a scan each over the block's text, then
   `opensWrapper`, which lexes a block opening with `<` alone (`isHtmlBlock`, one Lexer.lex) and parses an html
   token's block with DOMParser, the block's source with the probe paragraph appended, so a frame over the same text
   costs a table read per block asked, the whole-block lex and parse once per html block over the life of the source,
   and a paragraph's row its two scans once (before the memo a large html block with any block after it, an .html or
   .xml file ending in a comment, a note with one big html block, was lexed and parsed whole on every frame, about 15
   ms of a 16.7 ms frame in headless Chromium, 12 lexes and 12 parses in 12 frames over the stand-in and 12 parses
   over the real viewer, 20 ms of script over those frames for a 300-row table against 2 with the answer kept, 24 and
   24 from a fold's row with the block after the fold, whose carry asks it twice; the document's last block is never
   asked, `nextShown` stopping before it, so a file that is one html block cost nothing either way); and the picture's
   carry (`Place.pic`, item 1b) asks `opensWrapper` of no block a second time since the review's round 5, the `<img`
   line being looked for in the run `nextShown` already walked (round 4's carry had asked it once more of the top
   row's block whenever the row read as the block after it and an `<img` tag started at or after the row in that
   block, a lex and a parse more per frame, counted over the real viewer at 701728eae in round 5, the round 4 recheck
   and both refuters agreeing: 24 lexes and 24 parses in 12 frames with the opener, an `<h1>` or `<p>` lead row, the
   `<img>` row or the blank before the opener of a centred div holding an `<img` on top, 12 in 12 with an opener whose
   block held none and with a comment block holding `<img`, 0 in 12 with a plain or nested paragraph, the `</div>`
   closer or a comment alone; round 3's 12 in 12 for the opener row was of a tree before round 4 widened the carry,
   and a count is never carried from an earlier tree). Counted over the round's final code with a DOMParser hook, 12
   single-pixel scroll steps in Raw at 900, one frame each, before the memo above kept the answer (since it, one parse
   per wrapper block per source and none per frame after the first): 12 parses in 12 frames with any row of a single
   wrapper's run on top, the banner README's opener row, its `<img>` row, the blank before the opener, a no-picture
   README's opener, a comment's row before the opener, a `</div>` closer before a second wrapper and the inner opener
   of a wrapper two deep; one parse per wrapper block in the run, 24 in 12 with the OUTER opener of a wrapper two deep
   (two wrapper blocks in the run, one parse each by `nextShown`, none by the carry); and 0 with a nested paragraph
   row; the DOM decode of a character reference outside the table (item 4, `domRefText`) is one `<textarea>` innerHTML
   per distinct reference, memoized; and the `Place.lead` carry and seat (item 1b) read one box per row of the block's
   own at the edge, the boxes the picture's carry already read; the fold table (`foldDepths`) is one pass over the
   blocks per source, kept for the last source read as the anchor map keeps its block table, so a frame over unchanged
   text reads the table without rebuilding it (the review's round 2); in the fallback (item 4) `renderedBlocks` writes
   out the scope's blocks once per fallback paint, linear in the scope's source, through the lexer's cached tokens
   (`sourceTable`), and the whole document once more when the count guard widens (the review's round 3, in place of
   round 2's bounded emphasis passes over the strip). Tests, by file (every new node test on the shim's stand-ins with
   hideEdges; every browser leg over headless Chromium and the real bundles, 0 skipped, counted on every run):
   anchor-map-wrappers (38, four from the review's round 1, five from its round 2, eight from its round 3, seven from
   its round 4 and four from its round 5, test 27 re-aimed), anchor-map-html-text (7, new in the review's round 4,
   test 6's inline-title pin re-aimed in its round 5), anchor-map-html-rules (15, six new in the review's round 5, two
   from its round 6, five from its round 7 and two from its round 8), anchor-map-pairing-r6 (20, four new in the
   review's round 6, two from its round 7, three from its round 8, four from its closing pass, four from its closing
   pass 2 and three from its closing pass 3), anchor-map-html-text-browser (1 leg, 85 subtests, new in the review's
   round 5, three shapes from its round 6, sixteen shapes and two recorded entries from its round 7, three shapes and
   one recorded entry from its round 8), anchor-map-dom-rules-browser (1 leg, new in the review's round 5),
   anchor-map-wrappers-browser (6, one from the review's round 2, the panel open over a bare `<img>` block, and two
   from its round 3, the wrappers' leftovers and the open `<p>`, two scenes from its round 6, five from its round 7
   and nine notes from its round 8 in the round-3 test), anchor-map-fallback-markup (25, six new, main's projection
   case, two from the review's round 1, four from its round 2, five from its round 3, the corpus among them, and its
   verdict's pin from its round 4), anchor-map-code-table-paint-browser (4; its cards opened from their heads before
   Reveal's absence is read, the review's round 1; the round 2 cells, its round 2; the round 3 shapes, its round 3),
   anchor-map-obsidian (28, five new, the review's round 2's formula-first paragraph and its round 3's whitespace
   beside a formula), md-config-math-map-browser (6, one new and one from the review's round 2, its real triple-click
   re-aimed in round 3), anchor-map-change-marks (7; its count-guard scene moved off an attribute's text in the
   review's round 2 and onto a rendering that gained a copy in its round 3), md-config-paint-trim-browser (5, the
   confinement lifted), the fixtures anchor-map-fixtures/wrappers-plain.md, wrappers-2block.md, wrappers-unclosed.md
   (new) and blank-scenes.json (its note); file-view-place-blocks (14, two rewritten and main's projection case),
   file-view-place-html-browser (16, two rewritten, two from the review's round 2, one from its round 3, one from its
   round 4, five from its round 5, test 13 re-pinned in its round 7, one from the PR review's round 1),
   file-view-place-wrapper-end-browser (3, two rewritten), file-view-place-edits-browser (4, one tightened),
   file-view-place-closed-details (16, five from the review's round 5, tests 4 and 11 re-aimed in its round 6, test 12
   re-pinned and test 13 added in its round 7, one from the PR review's round 1) and
   file-view-place-closed-details-browser (10, both the review's round 1, extended in its rounds 2 to 4, the node file
   in its round 5 too), file-view-place-picture-line-browser (8, two new in the review's round 6, three from its round
   7 and three from its round 8, its test 6 at 700 too since the closing pass), file-view-place-last-fold-browser (1,
   new in its round 6); file-comments-overlap (5), file-comments-overlap-browser (1), file-comments-hint-order (9, one
   from the review's round 1, five from the PR review's round 1), file-comments-keyboard-offer (10, one from the
   review's round 4), file-comments-keyboard-offer-browser (3, one from its round 4), file-comments-paint-offer (9)
   and file-comments-paint-offer-browser (7; the paint-offer pair the review's round 1, all four extended in its round
   2, the browser leg's event count asserted in its round 3, one test and one leg added in each of its rounds 5, 6 and
   7 and two of each in its round 8), file-comments-unpaint-normalize (2), code-block-copy-keeps-selection (7, new in
   the review's round 6, three from its round 7) and file-comments-copy-fallback-browser (2, new in its round 6, one
   leg from its round 7), md-sanitize (17, two and the hook count from the review's round 4, the body title's unit
   test and the hook test's second body from its round 5, the fakes' projection from the PR review's round 1, which
   rewrote the title's two bodies), md-sanitize-comments-browser (2, new in its round 4) and
   md-sanitize-body-title-browser (2, new in the PR review's round 1), fileview-parity (the nested head),
   file-comments-anchors and md-config-paint-whitespace-browser (re-aimed), file-comments-behavior,
   file-comments-regions and file-comments-reveal-landing (pins on paintAll's shape re-aimed) and
   file-comments-about-review2 and file-comments-markclick-controls (their selection fakes read once);
   tools/file-review-plan.test.mjs, tools/file-review-plan-anchors-states.test.mjs and
   tools/file-review-plan-markclick.test.mjs (pins moved); tools/file-comments-host-anchors.test.mjs (14, two new),
   tests/test_file_comments_e2e.py (25, two new), tests/test_guide_files_keyboard_overlap_fold.py (8, new). Every case
   that changes behaviour fails over a `git archive` of a3edbaaf7 (the branch's base), of 40a4db43a for the review
   round 1's, of e5295ffa6 for its round 2's, of b1c6cb303 for its round 3's, or of 50b19bfdb, the second merge of
   main, for its round 4's, or of 701728eae for its round 5's, of 8924fa17e for its round 6's or of 78c0806ce for its
   round 7's, or of 6020e9309, the PR's reviewed head, for the PR review's round 1's, and says how in its commit; the
   guards say they are guards. The guarantees the families re-verify: highlights are measured `<mark class="fc-hl">`
   elements over the range's text nodes with their data-act, id, tabIndex, role and title, the margin layout reading
   their boxes (the walk, the raw needle and the cell gap change where marks appear, never their shape; the nested
   rule their paint, not their boxes); the pairing is the one table the reader's place, the change marks and the
   selection map read; the regions layer's span over a picture is in the index's shape at every depth; PRE and TD stay
   refused, so the fallback's ordinal keeps marking the changed cell or line under the raw needle and the pipe rule;
   the float, the composer and the save keep their rules under the keyboard offer and the composer's quote stays the
   exact source slice; and Slice 8's boundary stands (history since Slice 8, whose items 1 and 2 position the cells
   and the lines, so PRE and TD are no longer refused and the fallback's ordinal serves the unpositioned alone, and
   whose item 3 keeps the boundary at a selection across two cells of a table: the Slice 8 note).

### Slice 6: reaching a section without scrolling

`.fileview-body` takes `tabindex=0` and focus after paint unless the composer holds it; an Outline
action lists headings by level; per-path scroll memory, persisted with the Recent entry;
`openFileView(path, sid, { at })` (line, offset or heading) through the viewFile relay, sharing the
in-file link route's `:line` grammar (fork PR #347); a HEAD on focus and visibilitychange, showing "Changed on disk:
Reload" when the mtime moved and "Deleted on disk: Reload" when the HEAD answers 404 with the kernel's `missing`
reason (the words of the PR review's round 1, the reason its round 2, below). Acceptance: PageDown moves scrollTop
with no prior click; choosing the 40th heading in Outline puts it at the top; a note reopened from Recent returns to
its scrollTop; a todo link with a heading target opens at that heading; a moved mtime on focus shows the note bar.

**The Slice 6 build** (2026-09-13). Branch `mdviewer-s6`, cut from 4a3e18664, the head of `mdviewer-s8` (Slice 8, fork
PR 752, in the queue when the build began), every commit on it self-contained so that the branch could rebase onto the
fork's main once Slice 8 landed (the alternative of the brief's open question 1, taken so the build could start before
that landing, as Slice 8 itself was cut from Slice 5's head). After the build's consolidation commit it was rebased
onto main 0bf0465b4, the merge of PR 752, the branch's base since. Among the files this slice changes, 4a3e18664 and
0bf0465b4 differ in this plan alone (Slice 8's two review-round commits lie between them), so a run over a `git
archive` of 4a3e18664 reads the base's bytes in every file a test bundles or pins; the fork's main while the build
ran, 929ae86e1, differs from 4a3e18664 in six of them (docs/guide.md, this plan, ui/webview/feed.css,
file-comments.ts, fileview-parity.test.ts and styles.css) by Slice 8's hunks, so a run a commit records over 929ae86e1
ran over a tree without Slice 8's four parity heads and its guide sentences, and stands as that commit describes it.
The build's records had said every file the slice changes is byte-identical at 4a3e18664 and 929ae86e1 (this note as
committed, the ledger entry and the plan commit's message); the review's round 1 corrected the note and the ledger,
and the three commit messages that claim the identity for their own files alone hold, none of those files among the
six: 579fc2852 for file-view.ts (the commit also changes feed.css, fileview-parity.test.ts and styles.css, three of
the six, and its message claims nothing for them), 0f31a8759 and 9b1cf0d31 for every file they touch (the review's
round 2: round 1 had written this sentence with all three claiming it for every file they touch and none of them
changing a file of the six, both false of 579fc2852; the new tests/test_markdown_viewer_plan_note_history.py reads the
sentence and checks each claim against the history, and in a checkout without the history, CI's depth-1 one, holds the
sentence to the facts the module states, the skip named in the run's warnings summary; the review's round 3). The
rebase re-minted every commit, so the shas the commit messages name for their fails-before trees are trees no clone of
the fork reaches; the mapping, which `git range-diff` over the lineages reads as the same patch commit for commit,
with the build's label for each: 0302c727e (A1) is 579fc2852 on the branch, 9ac6a6f50 (A2) is 82e92a75f, 34b62b3f2
(A3) is 62f40046d, 52affc609 (B1) is 0f31a8759, 653df246a (B2) is 9b1cf0d31, fc5fde2b4 (A4) is 2d985c081, a40d4f4cc
(A5) is 0c6e6d11b, 7a03f202c (D1) is a491c4304, d79b3cf65 (D2) is 3204b0623, f6f9b6a4c (D3) is 4977730b2 and the
consolidation's c593ba950 is d91f0c19d. Those labels are the build's units, one builder each owning its files, under
one session that coordinated them: A the viewer (file-view.ts, the two sheets' viewer rules and the viewer tests), B
the Files pane, the link producers and the shell (files.ts, files-recent.ts, path-links.ts, render.ts, waiting.ts,
kernel.py's two viewFile forwarders, their tests) and D the records (the guide, this note and the ledger); the brief's
unit C, the comments panel, was not needed, the slice changing a header comment of file-comments.ts and none of its
code. A consolidation pass followed the units, the commit titled "Slice 6: build consolidation", which closed the
edges the units had recorded for it, ran the full test legs and wrote the build report; "the units recorded" and "the
consolidation pass" below name those. The items below are numbered as the build was planned: 1 the body takes the
keyboard, 2 the Outline, 3 the remembered place, 4 the open-at target, 5 the changed-on-disk line, 6 the records; a
reference to an item below is to that numbering, and "the brief" is the Slice 6 build brief of 2026-09-13, whose
seventeen open questions are cited by number with the default the build took.
The standing rule for the build: these changes cause the file-comments feature no trouble, which item 6's last entry
states as the guarantees every test family re-verifies. Where the code as built departs from the text above, why, and
which test holds each rule:
1. *Item 1, the body takes the keyboard.* `.fileview-body` is built with `tabIndex 0`, once per open and never touched
   again (the Comments panel's press-time strip takes the tabindex off the marks it walks up from a press, never off
   the body, so the attribute stands through a press; a press inside the body now lands the browser's focus on the
   body element, the nearest focusable ancestor, where it fell to the document's body before, and a drag begun on a
   highlight's first glyph still selects, measured in the leg). One helper in the open's closure, `takeKeyboard`,
   focuses the body with `preventScroll` after the open's first landing (text or media, spent once: a reload's landing
   never calls it; since the review's round 5 a text landing under a body with no box, the pane's document
   `display:none` while the fetch was in flight, leaves it pending for the width hook's repaint at the show,
   `landTarget`, since a `focus()` on such a body is a no-op and nothing held the keyboard until a click, measured in
   file-view-boxless-browser.test.ts's first leg) and after a paint the reader asked for from the viewer's own chrome
   (the Rendered/Raw toggle, a text-size step, the SVG Source toggle, and item 2's pick), and only when nothing, the
   document's body or a control in the viewer's own bar held the keyboard at that moment, read from
   `document.activeElement` and never from a flag (open question 5, the default): the chat's composer, the panel's
   boxes and every control in the aside, the editor's textarea or CodeMirror, a highlight, a card, a link inside the
   body and any element outside the card keep it; the panel's `setMode` repaints and a settings pick never call it,
   and the panel's own focus bookkeeping (the strip, the refocus at the release) runs untouched. Escape from the body
   closes the viewer through the document's handler as from the document's body. One departure from the brief's
   call-site list, forced by an existing pin: a text-size step from a KEY on the focused button (Enter or Space; the
   synthesized click's `detail` is 0) keeps the keyboard on the button, so the next press steps again
   (file-view-text-size.test.ts's third press from a focused A- had gone red under the unconditional hand-over); a
   pointer's step and a wheel step hand it to the body. Both sheets carry `.fileview-body:focus { outline: none; }` (a
   ring around the whole scroll box on every open would read as an error frame) and `.fileview-body:focus-visible`
   with a 1 px inset `var(--accent)` ring for the keyboard user (open question 6, the default), byte-equal and in
   fileview-parity's list. Two edges the units recorded were closed by the consolidation pass. In the chat modal the
   arrow keys reached render.ts's single-key shortcut, which scrolled the transcript behind the modal for every
   non-typing target (its type-to-compose handler stood aside for `#romp-fileview`; the arrow branch did not), so with
   the body focused ArrowDown moved the transcript and not the note; the branch now returns for the same three
   full-pane surfaces before it prevents the default, the note scrolls natively in every host, and the chat leg reads
   the body moved, the transcript box unmoved and the handler's scroller never run (over the tree before the guard it
   read body 0, transcript 60, the scroller run once); the review's round 1 moved that stand-aside ahead of BOTH arrow
   branches, keyed on every Arrow key, since it sat in the ArrowUp/ArrowDown branch alone and ArrowLeft or ArrowRight
   with the body focused stepped to the neighbouring session behind the modal (the file browser's ArrowLeft with no
   crumb above and a one-image lightbox's arrows stand aside from the tab step too now, the recorded three-surface
   set), and the chat leg reads `setActive` never called and neither key's default prevented with the viewer up, then
   the step to the second session after Escape. And the disk bar's Reload (item 5) took no keyboard at its landing:
   the click focused the button, the landing removed the bar with it, and the browser's fixup dropped the focus to the
   document's body, so a PageDown after that Reload scrolled nothing until a click; the Reload's click records who
   holds the keyboard BEFORE it disables the button (the review's round 1: a browser drops the focus off a control the
   moment it is disabled, Chromium synchronously to the document's body, so the consolidation pass's read at the
   landing found the body and handed nothing over in a browser), `dropDiskBar` hands it to the body on that record
   with `takeKeyboard` after the removal (the brief listed the button among the call sites), a keyboard held anywhere
   else (the panel's box while the poll's landing clears the bar) is left where it is, and a failed Reload, which
   removes nothing, re-arms the button and puts the keyboard back on it when the click had it and nothing holds it
   since (`keyboardIdle`: this document's active element null or its body, and no box being typed in a sibling frame;
   the review's round 2: the re-armed button took it back from a box the reader had moved to during the GET's flight,
   and the next Space fired Reload again), the re-arm running AFTER the failure pane's paint since the review's round
   3 (before it, a keyboard the reader had put on the old body's content during the flight, a link or a fold's
   summary, made the re-arm stand down, and the paint then removed that holder and dropped the keyboard to the
   document's body). Three more edges the units recorded were closed by the review's round 1, each with a test red
   before it: the editor's exits (Cancel, Save) repaint the text view and the body takes the keyboard as after a
   toggle (`exitEdit` calls `takeKeyboard` after its repaint; PageDown after Cancel had scrolled nothing until a
   click); the Outline's closers hand the keyboard to the body when the popover or the button held it (item 2); and
   `takeKeyboard` marks its own focus call, so the window focus it fires in a Files iframe that did not hold the
   page's focus sends no HEAD (item 5). The review's round 2 reached the rule into the sibling frame. In the Files
   iframe the chat composer is another document's, and this document's active element is its own body whenever the
   page's focus is elsewhere, so the same-document gate saw nothing to yield to and `body.focus()` pulled the page's
   focus into the Files frame, out of a box being typed in: a relayed open through a middle-click on a path pill (the
   mousedown's default prevented keeps the composer focused through the gesture), a Reload's landing after a move to
   the composer during the GET's flight and a Save's ack each cut a sentence (round 1 had recorded the relayed-open
   take as the slice's design, reading the brief's composer clause as same-document; the brief's rule is never over
   the composer, and the composer beside a Files iframe is the composer). `takeKeyboard`'s gate now also reads, when
   this document does not hold the focus, the top window's active iframe down to its own active element
   (`typingInPeerFrame`, module-level), and a textarea, a text-like input, a contenteditable or a `select` there
   (type-ahead in a dropdown is typing, as render.ts's own reading has it; the review's round 3) keeps the keyboard;
   any other holder there (the chat's body after a plain click, a focused button) yields as the document's body does,
   so the body still takes the keyboard for the acceptance, and a frame the read cannot see (another origin, a host
   with no top) or a read that throws takes it as before. Every hand-over runs through that one gate, the open's
   landing, the toggles, the Outline's closers, the editor's exit and the disk bar's drop, and the failed Reload's
   re-arm reads it through `keyboardIdle`; no relay field carries the sender's state. Since the PR review's round 1
   the Files pane toggled off and on (the shell's display:none on the pane; a phone's tab swap) hands the body the
   keyboard back at the show: the body's own focus and blur events keep the record of whether it held the keyboard
   (`bodyHeld`; a blur while the body has a box is a move the reader made and clears it, and the hide's fixup, which
   finds the body boxless, leaves it standing), and the show's repaint, over a text or a media body, hands the
   keyboard back through `takeKeyboard`'s gate when the record stands and nothing but the document's body holds it
   (`retakeAfterHide`), so a box being typed in beside the pane keeps it (the review's round 6 had recorded the drop
   and routed the re-take as a design extension; the PR review's round 1 ruled it into this slice, the edge being new
   to the branch; file-view-boxless-browser.test.ts's seventh leg, the landing giving the body the keyboard, the hide
   dropping it to the document's body, the show's repaint taking it back and PageDown scrolling, a textarea focused
   before the hide keeping it, the same for a picture, red over a `git archive` of 3e433ceee at the show's repaint;
   measured in the boxless harness's model, the overlay hidden by a rule, as the earlier boxless legs are). Edges
   recorded and not built: the fetch-failure pane takes no keyboard; a `button`-typed opener outside the card would
   keep it, and a span opener
   reached by Tab and activated by Enter keeps it today (`pathLinkPress` drops the span's tabindex for a pointer press
   alone, so a pointer's opener, a pressed span or a `div` row, drops the focus to the document's body and the body
   takes it, while a keyboard activation leaves the focus on the span: in the chat modal the body then does not take
   the keyboard and PageDown scrolls the transcript behind the modal, where a relayed open into the Files pane reads
   that span through `typingInPeerFrame` as a holder that is not a typing box and takes it; the default stands, open
   question 5's, any element outside the card keeping the keyboard, and the case is routed with the button-typed
   opener; the review's round 3); the URL viewer's body is not a Tab stop (the brief scopes the item to openFileView;
   the two sheet rules reach it by class). The ring (the review's round 3; the build had measured, not asserted, that
   Chromium's `:focus-visible` heuristic shows it on a script focus with no prior interaction and that a relayed open
   before any click may show it): Chromium's heuristic for a script focus matches `:focus-visible` on the new holder
   when the old one wore it or a key was pressed since the last mouse press, which is right, and ALSO when nothing
   focusable was last pressed, so the ring framed the whole note in the accent on every pointer-driven open where that
   held, a pill's click in the chat and feed modals (the press strips the pill's tabindex), every relayed open (the
   click was in another frame) and every open after Escape or a click on plain text (a Recent row is a plain `div`);
   `takeKeyboard` now names the ring through the focus call's `focusVisible` option, read off the holder it takes the
   keyboard from (`ringOf`: a holder wearing the ring, a Tab-focused toggle activated by Enter or the Outline popover
   after its arrow keys, passes it on; a mouse-focused control passes none; with no holder, the document's body
   holding the keyboard, the kind of this document's last press decides, a key that is not a modifier alone passing
   the ring and a pointer none (`watchInputKind`, installed once by `initFileView` on the document's capture-phase
   keydown and pointerdown, read by `ringWithNoHolder` only while this document holds the page's focus, so a relayed
   open still passes none and no relay field carries the sender's state; the review's round 4: round 3 had passed none
   for every holderless hand-over, and Enter on the file browser's active row, whose rows are not focusable, lost the
   ring the browser had drawn at 27c56fbf7); a closer that removes the holder first reads the ring first, the
   Outline's closers and the disk bar's Reload at its click, before the disable drops the focus, and the replace path
   reads a holder inside the old card before the removal, `ringInOld`, for the open's first landing to pass (round 4:
   Enter on a Tab-focused path link inside the note had lost it, the link gone before the fetch landed)), a Tab into
   the body earning it natively as before. The option's verdict holds for the life of that focus, keys included, where
   Chromium's heuristic gives a mouse-focused element the ring on its first key, so a body handed the keyboard without
   the ring showed none after any number of keys (the review's round 4; the code's comment had claimed the opposite):
   the body's own keydown takes the keyboard again naming the ring on the first key that is not a modifier alone and
   carries no Ctrl, Alt or Meta, a blur and then a focus with the ring and `preventScroll`, since a re-focus of the
   element that holds the focus changes nothing in Chromium; the key's own scroll follows, a selection inside the body
   stands, and a chord (Ctrl+C over a selection) lifts nothing, as the heuristic has it. The sheets' two rules are
   unchanged, their comment stating the mechanism, and a browser without the option ignores it. Cost: one attribute
   per open, one `focus` call per gesture, and a blur and a focus on the first key after a ringless hand-over.
   file-view-seam.test.ts (39, three new here: the stand-in gained `focus` counting, a `tabIndex` accessor and the
   browser's focus fixup for a removed subtree), file-view-focus-body-browser.test.ts (3 legs, new: the pane at 900
   and 380 px with no click, PageDown, Space, ArrowDown, End, Home and Escape, the Tab ring in the accent and none for
   a pointer's press, a press on a path link landing the focus on the body and the replace-open handing it to the new
   body; the chat modal under render.ts's own key handlers lifted from source, the composer keeping the keyboard it
   held at the open and taking a typed letter after Escape, ArrowDown moving the note alone, ArrowRight and ArrowLeft
   stepping no session and keeping their defaults with the viewer up and ArrowRight stepping to the second session
   after Escape; the panel's mid-press reading of the body's tabindex 0 and the mark's absent, the release focusing
   the mark, the comment box keeping the keyboard through a Raw paint), fileview-parity.test.ts (4, the two heads),
   file-view-place.test.ts (8, the text-size bracket's pin re-aimed), file-view-keyboard-frames-browser.test.ts (2
   legs, new in the review's round 2: a shell stand-in with a chat iframe holding a textarea composer and a plain
   paragraph beside the real Files pane page, the Files frame's GETs held by the test for the mid-flight scenes; the
   relayed open with the composer typed in leaves the composer holding the keyboard and the chat document the page's
   focus, no HEAD, the typed letter reaching the composer and Space scrolling no note, a click in the note then
   landing the keyboard on the body; a plain holder in the chat frame yields and PageDown scrolls with no click; the
   Outline popover closed by a click into the composer leaves the composer holding it; the Reload's landing after a
   mid-flight move to the composer, a failed Reload's re-arm (the button not focused, Space firing no second Reload)
   and the editor's exit at a Save's ack each leave the composer holding it, the next letter reaching it; the
   plain-holder and Outline scenes are guards, green over the c88444f85 archive when run alone, and the leg's header
   and scene comments say so since the review's round 3), feed-viewer-focus-browser.test.ts (2 legs, new in the PR
   review's round 1, over the real feed bundle in a shell stand-in with the served ids f-chat and f-feed and a chat
   iframe holding a textarea composer: the finding the round left to be settled, that the feed's click listener hands
   the page's focus to the chat frame after a click in the viewer or the browser, is measured and refuted; with the
   composer typed in, a click on the note's text, on the Raw toggle, on the Outline button and on a file row of the
   browser each register the listener's zero timer, and after it fires the feed document still holds the page's focus,
   the body or the popover the keyboard, PageDown scrolls the note and the composer takes no letter; a relayed open
   over a plain holder lands the keyboard on the body and one with the composer typed in leaves the composer holding
   it; the control, the hand-back's call made by hand at the top window, moves the page's focus onto the chat's body,
   not the composer, since Chromium clears a frame's focused element when the focus moves into another frame; the
   hand-back is inert because returnFocusToChat looks the chat frame up by an id the served shell does not carry, a
   pre-existing condition outside this slice, and a scratch run with the id corrected turns the four post-timer reads
   red while adding a boardCovered exception to feedWantsKeys turns them green again, the fix if the lookup is ever
   corrected; green over the 3e433ceee archive and at the fix head, a record and not a fails-before),
   file-view-focus-ring-browser.test.ts (3 legs, two new in the
   review's round 3, over real path pills and real presses: in the chat modal at 900 and 380 px and the feed modal a
   mouse click on the pill on the fresh page, after Escape and after a click on plain text leaves the body holding the
   keyboard with no ring, a Tab from the bar earns the accent ring, a Raw toggle focused by a key and activated by
   Enter hands over with the ring and a mouse click on Rendered without; in the Files pane at 900 and 380 px an open
   with no gesture and one after a click on plain text show no ring, an Outline pick by End and Enter lands with the
   ring and one by mouse without; 0/2 over the tree before the fix, the ring read on the fresh page's pill click and
   on the pane's gestureless open; a third leg in the review's round 4: in the chat modal, the feed modal and the
   Files pane at 900 px, after a pill click or a gestureless open PageDown brings the accent ring and the key's own
   scroll, a mouse click on A+ hands over ringless and ArrowDown brings the ring back, a mouse click on A- hands over
   ringless and Ctrl+C over fourteen selected characters brings none and keeps the selection, which stands through the
   next ArrowDown's lift; red over a `git archive` of 7fbced030 at the first PageDown),
   file-view-focus-ring-openers-browser.test.ts (2 legs, new in the review's round 4: in the Files pane and the chat
   modal at 900 px a Tab to the in-body `./notes.md` link and Enter replace the viewer with the new body holding the
   keyboard with the ring, kept through the keys that follow, and a mouse click on the same link without; in the pane
   the real file browser, bundled beside the viewer, opened by ArrowDown and Enter lands with the ring and by a mouse
   click on a row without, the gestureless open and the open after a click on plain text still without; at 700 px in
   both surfaces the changed-on-disk bar's Reload by Tab and Enter lands the body with the ring and the bar gone, and
   a mouse Reload without; the first leg red over the 7fbced030 archive at the link's Enter and the row's Enter, the
   second a behavioural pin of round 3's record, green there).
2. *Item 2, the Outline.* A markdown file's actions row gains an `Outline` button right after the Rendered/Raw toggle
   (the plan's word kept as the label, open question 2's default; the guide's sentence says "the file's headings"
   since the guide's "The outline" is the sessions pane), `aria-haspopup="menu"`, `aria-expanded` and the bar's
   selected class `on` while the popover is up (the class since the PR review's round 1: the Sheets sentence below),
   `title` "The file's headings", appended for a markdown file only and hidden unless the Rendered view is painted
   with at least one heading and the editor is down (open questions 4 and 16, the defaults; Edit switches a note to
   Raw, so after Cancel the button stays hidden until Rendered is chosen again). A click flashes it and opens a
   pane-local dropdown in the menu vocabulary (the `--menu-*` tokens, 12 px, `.ctx-menu` the reference, no literal
   colour): every `h1` to `h6` under `.fileview-md` in document order, read off the Rendered DOM at the open and never
   per paint (open question 3, the default: a heading inside a fold, open or closed, or a quote is listed as the DOM
   holds it; a heading under a wrapper carrying a plain `hidden` has no box to land on and no row, where
   `hidden="until-found"`, which a landing lifts, keeps the row, and a note whose only heading is hidden shows no
   button, since the review's round 3, when the row was offered and its pick closed the popover and moved nothing; a
   formula heading shows KaTeX's text with its U+200B struts stripped; the front-matter block is a `details` with no
   heading and has no row, the Slice 4 map's worry verified closed), one row per heading with its id, an id of its own
   (`fileview-outline-<open>-<i>`, unique per open of the popover, which the popover's `aria-activedescendant` names
   at the open and on every move, so assistive technology hears the current row where the menu had opened and moved in
   silence; the review's round 3), its text on one line (each picture read as its alt text in place, so `## ![Figure
   3: latency](figs/l.png) (detail)` reads "Figure 3: latency (detail)", the heading's accessible name; an image-only
   heading's row reads its pictures' alt text, and one non-breaking space with none, so the row keeps a text row's
   height; the review's round 1: the image-only row was an 8 px blank strip; round 3: a heading with a picture and
   text beside it had dropped the picture's name) and its depth under the note's shallowest heading. The popover is
   `position: absolute` inside the card, placed from the button's box against its containing block, read as its
   `offsetParent` after the append: the viewer's fixed overlay, since the card's `container-type` gives it no layout
   containment in Chromium (the review's round 1; the build placed it from the card's edges, and in the chat and feed
   modals, where the card is inset from the overlay, the box sat 18 px too high over the button's lower half and 25 px
   left of its anchor). It is capped at the body's height less 16 px and the card's width less 16 px, and a
   right-anchored box that would start left of the card's 8 px margin (a 45-character heading at a 900 px pane, 33 at
   380 px: the browser solved `left` negative and the card's overflow clipped the start of every row) is anchored at
   that margin with the width still capped, read after the placement, so every row starts inside the card and a
   heading wider than the card takes the rows' ellipsis (the review's round 1). It scrolls within itself and is
   focused at the open with the section under the reader's eye current (the PR review's round 1 ruled so, that being
   what an outline is for: `underEye` picks the last heading with a box whose top is at or above the body's top edge
   plus the heading's `scroll-margin-top`, read once, so a heading a landing just put at the top is the section, a
   heading with no box, inside a shut fold, is passed over, and the first row is current when none qualifies; the
   build had started at the first row, the brief's keyboard case, "ArrowDown twice then Enter picks the third row",
   reading so, and that leg's ArrowDown step now scrolls the body to its top first; file-view-outline.test.ts's ninth
   case, heading 31 at the edge making row 30 current and named by `aria-activedescendant`, one px under it the
   previous boxed heading, a shut fold's block at the edge the last boxed heading before it, scrollTop 0 row 0, and
   file-view-outline-browser.test.ts's first leg, the reopen after the 40th pick reading row 39 current, both red over
   a `git archive` of 3e433ceee, 0 where 30 and 39 were expected). ArrowDown and
   ArrowUp move the current row within the popover's own scroll, Home and End jump, Enter and Space pick, Escape
   closes the popover and puts the keyboard back on the Outline button (the menu-button pattern its
   `aria-haspopup="menu"` announces; the PR review's round 1: the build had handed it to the body, and
   file-view-outline.test.ts's fourth case and the browser suite's first two legs read the destination), and Tab and
   Shift+Tab close the popover and put the keyboard back on the Outline button with the key's default left to run, so
   the browser moves on from the button to the next or the previous control in the bar, as
   from a menu button (the review's round 3: the popover was the card's last child, and a Tab from it left the viewer
   for the first focusable behind the dimmed modal, the chat's composer, which took the letters typed); every other
   key it takes is prevented and stopped on the popover, so the document's handler never closes the viewer on that
   Escape and the chat's window handlers yield. The pick closes the popover, lands the heading through the fragment
   landing's own steps (`scrollToFragment`: `revealFragmentTarget` opens the folds above it, then `scrollIntoView`
   block start, so the heading's top sits at the body's edge less its 10 px `scroll-margin-top` in both sheets, where
   a `#` link puts it, not at the pixel edge; a heading with less text below it than the body shows lands where the
   scroll clamps) and returns the keyboard to the body, so PageDown reads on from the section. Closers: a pick,
   Escape, a capture-phase pointerdown on the document outside the popover and the button, focusout to anything but
   the button (a Tab out does not leave it standing; a window losing the focus closes it too), a window resize, every
   paint of the body (a reload's paint rebuilds the headings the rows name, not only a view switch) and both exits.
   Since the review's round 1 a closer that removes the popover while it or the button holds the keyboard hands the
   keyboard to the body through `takeKeyboard`'s gate (`closeOutlineKeeping`: the resize, the paint, the button's
   second click, whose mousedown had focused the button; before it the browser's fixup left the keyboard on the
   document's body, where PageDown scrolled nothing and the chat's bare-area Enter reached the composer), the focusout
   closer excepted when the keyboard moved to another element, which keeps it (a window losing the focus hands it to
   the body for the return; a move into another frame, the chat composer beside the Files pane, has this document's
   active element already cleared when the focusout fires, so the closer reads no holder and the frame's own holder
   keeps it, the review's round 2's reading of the null case, pinned in the two-frame leg, and since the PR review's
   round 1 each of the closer's three branches is executed in file-view-outline.test.ts's tenth case: a move inside
   the popover or onto the button leaves it standing, a move to another element of the document closes it with that
   element keeping the keyboard and the body taking nothing, and a null relatedTarget while the popover holds it
   closes it and the body takes it in one focus call, a guard green before the round and red under three mutations of
   the closer, the stand-aside line deleted, the listener deleted and the null reading flipped); and the fetch
   pipeline's
   failure pane closes the popover and calls `syncOutline`, so the popover and the button go with the headings they
   listed (the review's round 1: the button stood, inert, over a 404 a reload painted; round 2: the catch paints the
   pane without `renderBody`'s closer, so a popover open at a failed reload stood over the pane with its stale rows
   and the keyboard, the hidden button reading expanded; `closeOutline` runs before the pane's paint and the body
   takes the keyboard the popover held). Nothing is stored and nothing is read from the source. The popover, a child
   of the card, is under the landing's press hold since the PR review's round 1: the hold is `pressHold(box)`, the
   card's, in place of the body's, so a fetch landing while a row is pressed (the Comments panel's poll, a reload)
   parks until the release and the pick lands, where before the landing's paint ran `closeOutline` and removed the
   pressed row before the mouseup and the click was lost, the click-safe failure ui/CLAUDE.md names; the card's
   listener now hears a press before the body row's, and the raise's order in item 5 holds by the parked landing's
   settle, not by which hold hears the press first (file-view-outline.test.ts's eleventh case and
   file-view-outline-browser.test.ts's fourth leg, the mouse down on row 40, a reload through the seam, the popover
   standing with no paint, the release picking and landing the heading at the top and the new bytes painting after
   with it kept there; both red over a `git archive` of 3e433ceee at the popover standing under the press). Since the
   PR review's round 2 a landing the hold PARKED opens the popover again after its paint when one is open at its run:
   the card's hold also parks a landing under a press on the Outline button itself, whose click, run before the parked
   run's zero timer, opens the popover, and the landing's paint then closed it (every paint closes it, its rows read
   off the DOM the paint replaces), so the click appeared to do nothing; `fetchFile`'s `land` reads the hold once
   before the defer and hands the run a `parked` flag, and the text landing, when the flag is set and a popover is
   open, calls `openOutline` after `landTarget`, rebuilding the rows and the current row over the landed body with the
   keyboard on the popover as the click left it; a landing that ran at once still closes it, and one parked under a
   press on a row, or on the button with the popover up, finds it closed by the pick or the toggle and opens nothing
   (file-view-outline.test.ts's fifteenth case and file-view-outline-browser.test.ts's fifth leg, the press on the
   button, the reload landing parked with no paint, the release's click opening the popover on the old note and the
   parked landing's one paint leaving it standing with the landed note's rows; both red over a `git archive` of
   e6aeb1138 at the popover standing after the paint). Measured: a 500-heading note's popover opens about 9 ms after
   the click in headless Chromium (one query, 500 rows; the leg prints the number and asserts a loose bound so a
   loaded box cannot flake it); the Outline adds one hidden button per markdown open and one `querySelectorAll` per
   text paint for the button's visibility (open question 17). Edges: the URL viewer's actions row has no Outline (the
   popover lives in openFileView's closure). menu-theme-tokens.test.ts's list of menu surfaces names the popover's
   card and its row wash in both sheets since the consolidation pass (a guard, green before: file-view-outline.test.ts
   applies the same dark-literal ban), so the two blocks are read with every other menu. One fix from the
   consolidation pass, found by the full npm test: the button's visibility was decided at the top of `renderBody`
   (hidden) and again after the paint (`syncOutline`), and it is the one bar control that differs between the two text
   views; at pane 900 the actions row wraps with it (the bar 64 px in Rendered against 40 px in Raw, measured; the
   chat modal's bar wraps in both views), so hiding it before the paint read the reader's place grew the body and
   re-clamped a body standing at the document's end, and the held place was lost: the Rendered/Raw round trip from the
   end came back one paragraph early and a last fold's row 523 px low (file-view-place-blocks-browser and
   file-view-place-last-fold-browser, green on origin/main and on the A4 head fc5fde2b4, red at the A5 head a40d4f4cc
   and alone; both heads of the pre-rebase lineage, mapped at the head of this note). A text paint now decides it
   after the swap and the tables' width stamp and before the hooks measure and the seat writes, and only the paths
   that paint no text (the loader, the editor's entry) hide it at the top; the order pins name the new step
   (file-view-place.test.ts (8, two re-pinned), file-comments.test.ts (35, one order pin re-aimed),
   file-view-outline.test.ts's own). Accepted cost, not a defect (the review's round 2): the Outline button is one
   more control in the bar's wrapping actions row, and a control of width w moves every step of the bar's height
   staircase right by w. Measured over the real bundles of main 0bf0465b4 and the branch (the Files pane 600 px tall,
   a nine-heading note, the Comments panel closed and open): the row's natural one-line width is 725.4 px on main and
   790.0 on the branch (the button 58.6 plus the 6 px gap), so the one-action-row step, between 745 and 750 px on
   main, lies between 805 and 810 on the branch, and the actions-beside-the-path step moves from between 885 and 890
   to between 950 and 955; between the steps the trees agree, and a note with no heading is identical at every width.
   The 300, 800 and 900 px cells of the round 1 matrix (157 against 126, 95 against 64 and 64 against 40 px) are those
   shifted steps. Nothing was changed: the label and the place in the bar are decided defaults (open questions 2 and
   16), the only rules that keep one row at exactly 800 px shave 15 px or less of slack (the reset slot's 5.5em, the
   row's gaps) and move the step by that much, and a leg pinning a one-row bar at 800 px would rest on a sub-15 px
   margin of font metrics, which differ between the maintainer's box and CI. Sheets: `.fileview-outline`, its
   `:focus`, `.fileview-outline-row` and the hover and current wash, byte-equal and in fileview-parity's list; the
   Outline button wears the bar's selected dress, `.fileview-btn.on`, while its popover is up (file-view.ts toggles
   the class beside aria-expanded, and puts it on BEFORE the popover's box is read: the bold dress widens the button
   by a few px, and in the chat modal at 1000 px that re-wrapped the actions row and moved the button down a line, so
   a popover placed from the pre-dress box sat 20 px above the button's bottom, measured in the browser leg) and has
   no rule of its own since the PR review's round 1, which dropped the build's `[aria-expanded="true"]` rule, a
   near-twin of that dress without its 600 weight and hover inversion (the build's own review, round 1, had narrowed
   that rule from the bare `.fileview-btn`, which recoloured the Comments panel's Show less and armed Reject all, bar
   buttons that carry aria-expanded too, a comments regression in the Rendered view, to `.fileview-outline-btn`); the
   `.fileview-btn.on` and `.fileview-btn.on:hover` heads join fileview-parity's list, whose new case holds the twin
   gone (red over a `git archive` of 3e433ceee, the twin's head found in styles.css), and a headless-Chromium probe
   read an open button with the class computing as the pressed Rendered toggle does in both sheets, at rest and on
   hover once the bar button's transition had finished, while aria-expanded without the class computed as a plain bar
   button. file-view-outline.test.ts (15, new: the real openFileView over the place suite's stand-in, given heading
   ids by the sanitizer's own two slug functions; the button's placement, aria and hiding, the 42 rows with ids,
   texts, depths, the fold's and the quote's headings and no front-matter row, the pick's landing and keyboard return,
   the fold opened, the keyboard, the closers, source pins over both sheets; from the review's round 1, the sheets'
   heads for the button's open state, re-aimed in the PR review's round 1 to every `.fileview-btn.on` head in both
   sheets reaching the open Outline button and none of the panel's Show less, armed Reject all or Show more, with no
   head in either sheet naming aria-expanded or the button's class; from the review's round 2, both sheets' Outline
   comment naming `offsetParent`, `#romp-fileview` and no layout containment and none of the stale
   card-as-containing-block phrases, and the failure pane's paint closing an open popover, the button hidden and
   collapsed and the body holding the keyboard; from the review's round 3, the hidden heading's row absent and the
   `until-found` one listed, a note whose only heading is hidden showing no button, the rows' ids present and unique
   per open with `aria-activedescendant` following ArrowDown and End, a heading with a picture and text reading the
   alt in place, and Tab closing the popover onto the button with the event neither prevented nor stopped; from the PR
   review's round 1, four new cases, the current row at the open, the focusout closer's three branches (a guard, red
   under three mutations of the closer), a landing under a press on a row waiting for the release, and a heading under
   a plain `hidden` wrapper opened at it showing the ruled words with the export, role status and nothing scrolled,
   three re-pinned, Escape's destination the button, the `on` class while open and gone after the toggle, and the
   sheets block's slicer ending at the row-hover head with no aria-expanded rule in the block, and the sheets case
   rewritten for the reused dress; the stand-in's events carry `button` and `relatedTarget`, both hidden from the
   assertion differ; from the PR review's round 2 the fifteenth case, the press on the Outline button with the landing
   parked under it, and the source-pin case 7 reading the re-open lines, `land`'s `parked` flag and `openOutline`
   called from the toggle and the re-open alone), file-view-outline-browser.test.ts (5 legs, new: the pane at 900 and
   380 px and the 500-heading cost, the tokens' computed colours in the dark and the light theme, the 40th row at the
   top; the chat modal under render.ts's own key handlers; from the review's round 1, long headings at pane 900, pane
   380 and chat 1000 inside the card with every row's text starting inside the popover and the 90-character row
   ellipsized, the usual note's right anchor 4 px under the button in the pane and the chat modal, an image-only
   heading's row reading its alt text at a text row's height, the resize closer, the panel's reload closer and the
   toggle close leaving the body active with PageDown scrolling, and the failure pane hiding the button, since round 2
   with an open popover closed by its paint, the hidden button collapsed and the body holding the keyboard; from the
   PR review's round 1 a fourth leg, a landing while the pointer is pressed on a row waiting for the release, and two
   re-aimed, the first leg's reopen after the 40th pick reading row 39 current and Escape leaving the keyboard on the
   Outline button in the first two, the press pulse's class allowed; from the PR review's round 2 a fifth leg, the
   press on the button in headless Chromium, a reload through the seam under the press, the release and one paint with
   the popover standing over the landed rows), the fixture ui/webview/file-view-outline-fixture.ts (42 headings,
   test-only), fileview-parity.test.ts (4, the Outline's heads; since the PR review's round 1 the two
   `.fileview-btn.on` heads in place of the twin's, and a case holding the twin gone), menu-theme-tokens.test.ts (7,
   the Outline's two blocks in both sheets added to its surfaces by the consolidation pass); real-viewer-leg.ts
   exports `chatKeysScript()`, the chat page's window key handlers lifted from render.ts, shared by items 1 and 2's
   chat legs.
3. *Item 3, the remembered place.* The memory is the reader's place in the file's terms, with the pixel count as the
   fallback (open question 7, the default): `RememberedPlace`, exported from file-view.ts, is the top block's source
   span and its top edge's offset from the body's top in px, whether the body stood at its very top, the view it was
   read in, the file's mtime string when read, the numeric scrollTop, the time and, for a read in the Rendered view of
   a note with a fold, `folds`, the ordinals in document order of the `<details>` the reader had open (numbers only;
   since the review's round 3, below); never text (a JSON of a record holds no word of the file, pinned).
   `rememberedPlaceOf(place, mtimeNs, scrollTop)` makes one from a reader-place `Place`; `placeFromRemembered(rec,
   source)` gives a Place back over the file's text as it is NOW when a block of that text STARTS where the remembered
   one did (an edit inside or below the block keeps it), null otherwise. The viewer keeps one record per file for the
   page's lifetime, keyed by `placeKey` (exported): the path as openFileView receives it, and the session too for a
   relative path, which the kernel resolves against the session's cwd (`_resolve_open_path`: neither `/`- nor
   `~`-rooted), so two sessions' `docs/report.md` are two files, while an absolute or `~` path shares the key across
   the sessions of one kernel, the same bytes being the same file there, and a session attached from another kernel (a
   `host:`-prefixed sid, host-prefix.ts's `hostOf`, whose read goes to that kernel's disk) has the host folded into
   its key, the host, a NUL and the path, so the two kernels' files are two files (the PR review's round 1 ruled
   correctness over sharing, closing the review's round 6 record of two files under one key; a relative path's key
   already tells the kernels apart, its sid being the prefixed one; the review's round 2: the build keyed by the path
   alone, and a second session's relative path, never read, opened at
   the first session's place; the host still hears the path as written and the session), and writes it at the moments
   the reader leaves a file: `closeFileView`, openFileView's replace path, openUrlView's replace path (each once the
   close guard has passed, before the old body goes) and the window's `pagehide` (installed once in `initFileView`
   beside the module's other window listeners; it writes without retiring the viewer, since a page back from the cache
   still shows it). Each write reads the place once (`keptPlace`, one `readPlace`, never per frame; measured in the
   node test as exactly one body rect read at the close and none per scroll frame, the Slice 5 lesson), while the
   editor is up the leave writes the place of the text view Edit replaced, read at Edit past the refusal guard and
   before the Raw switch (`editPlace`, cleared at the exit; the review's round 2: the build wrote nothing while
   editing, its buffer not being the text, so a close from the editor with a clean buffer, a page hidden while editing
   and the conflict bar's Reload forgot the read, and the reopen fell to the top or to the read before it; and since
   Edit saves the Raw preference, the reopen after a close from the editor paints Raw over that Rendered record and
   seats the block's first row at the edge, the depth staying behind as it does across views, and the Raw close then
   writes a Raw record, so a later Rendered reopen seats the block at the edge, the review's round 3, which pinned the
   reader's own sequence in place-memory case 6 in place of a reopen under a cleared preference; a leave AFTER the
   editor's exit reads the body as it stands, the record being the reader's place at the leave, so Edit then Cancel or
   Save and then a close records the top of the file, because `exitEdit`'s repaint lands the text view at the top: its
   `renderBody` reads `keptPlace` over the editor's body, which `readPlace` cannot read, so the seat lands at
   scrollTop 0, and a person at paragraph 40 who clicks Edit then Cancel sees the Raw view open at the heading, on
   main 0bf0465b4 and the branch alike, pre-existing and outside the items, the place across the editor being Slice
   2's rule; the routed fix, seating `editPlace`, which Edit already reads, at the exit's repaint through
   `landRemembered`, cures both, recorded in the review's round 3 and not fixed), and never without a text view (a
   picture, a PDF frame, the loader, a failed fetch; the SVG Source view is a text view and counts). `initFileView`'s
   host gains `onLeave(path, sid, rec)`, and `openFileView` gains `opts.place`, a record the host hands back; of the
   host's record and the memory's the later `t` seats, null or undefined meaning the memory stands; an open with `at`
   lands on its target and ignores both, and its leave still writes (open question 9, the default). Two departures
   from the brief's sketch, each forced by what a record does not carry: the seat runs right after the first text
   paint's own `seat(kept)` (`landRemembered`), not through `keptPlace()`, so the paint's pinned order stands and a
   remembered open costs one more `readPlace` on its first paint; the block's height is not kept, so the depth into
   the block is applied in pixels (the top edge at the record's offset when at or below the edge, else at the edge and
   then scrolled by the offset) and only when the open's view is the record's, the block's top landing at the edge in
   the other view (an unchanged file at the same width comes back to the pixel the browser snaps to; a changed width
   comes back near, not exact); and the source is not kept, so a block that text inserted or removed ABOVE it moved is
   not followed as a reload's place is (`followPlace` has the old text; the memory does not, by open question 8's rule
   against file text in the store): the numeric scrollTop is written and the browser clamps it. Since the review's
   round 1 the seat first opens the closed folds above the remembered block's elements, as the offset landing and a
   `#` link open them (`revealFragmentTarget`), and the block's own fold when the record's edge lay in its content (a
   depth in the record's view past the shut box the reopen paints: a shut fold's content is never at the edge, but its
   summary straddles it the same open or shut, so a depth inside the summary's own height says nothing and the fold
   stays as authored; the review's round 2: a shut callout or front matter whose summary straddled the edge came back
   open, thirty paragraphs taller): a reopen paints every fold as authored and the record carries no fold state, so a
   record read inside an author's `<details>` the reader had opened met no shown box, and the numeric fallback from
   the open fold's layout, clamped over a document the shut fold made thousands of pixels shorter, showed a passage
   thirty paragraphs past the reader's; a folded callout, one block, seated its summary at the edge and took the depth
   over a summary-tall box; a Raw record reopened under the Rendered preference opens the fold too, whatever the
   depth, every Raw row having shown, unless the body stood at the file's very top (the record's own `atTop`, the
   state a close from the editor leaves, where the front matter's block starts under the edge) or the block starts
   below the body's height (a Raw row read as the block after a run of comment or closing-tag rows can name a block
   under the view) (the review's round 3: the round 2 depth rule had left a folded callout shut with its summary at
   the edge for such a record, so `revealRemembered` now takes whether the open's view is the record's; round 4 keyed
   the rule on the block's top sign, `top` at most 0, since a Raw record left at the file's very top, the front
   matter's block starting under the edge, had unfolded the front matter on every Rendered reopen; round 5 reads the
   flag and the height bound instead, since the sign also left shut a callout whose rows the reader had in view under
   the blank row at the edge, which round 3 had opened; the bound compares the record's Raw `top` with the REOPEN
   body's clientHeight, so across two body heights, the Files pane and the chat modal, a rotated phone, a pane dragged
   shorter, a callout whose rows were in view in a tall pane stays shut on a short-body reopen and one whose rows were
   below a short body's bottom opens on a tall one, the review's round 6, which measured a twenty-row comment before a
   shut callout, a leave at 1100 px and a reopen at 300 px shut and the reverse open, through the
   module's memory and a Recent row's place alike; the record would need the leave's body height, a field the decided
   record does not carry, open question 7's spans, pixels and mtime, so it waits for a follow-up, recorded in item 6).
   Since the review's round 3 the record also carries the Rendered view's fold state: `openFoldOrdinals(body)`
   (exported) reads, at the leave inside `liveRecord` (so `editPlace` carries it too), the ordinals in document order
   of the body's `<details>` that are open, absent when there is nothing to record (a Raw read, whose rows have no
   folds, a note with no fold, a record an older store wrote), and `restoreFolds` puts every fold back as the reader
   left it before the seat when the file's mtime is the record's and the view is Rendered (the same bytes render the
   same folds, so the ordinals are exact); the rules above are the fallback for a changed file or a record with no
   fold state and stand down over a fold the record's state put back (`restoreFolds` says whether it applied; the
   review's round 4: a fold left shut at 380 px with the edge 50 px into its two-line shut box, reopened at 900 px
   where the box is one line, met a depth past the shut box and came back open, the reverse face of the width window
   round 3 closed), the depth rule alone since the review's round 6: the other-view rule runs over a fold the carried
   folds put back shut, a Raw record's carried folds being older evidence than its place, read at a Rendered paint
   before the Raw read named the fold's rows (round 6: a Rendered read with the callout shut as authored, Edit, a Raw
   read into its rows and a Rendered reopen kept it shut, its summary at the edge over the passage the rows had shown;
   fold leg 13, red over a `git archive` of 85fa51bf5, and the same for the front matter); a record's folds met by a
   Raw first paint (Edit saves the Raw preference, so the reopen after a close from the editor paints Raw over a
   Rendered record; the preference switched elsewhere between the leave and the reopen the same) are held for the
   open's first Rendered paint and put back there at the record's mtime, right after `foldKeeper`'s restore
   (`pendingFolds`, `restoreHeldFolds`; round 4: the toggle after such a reopen had painted every fold as authored,
   the summary at the edge over the passage the Raw row had named); a first text paint under a body with no box (the
   pane's document `display:none` while the fetch was in flight, a phone's tab swap) keeps the record pending for the
   width hook's repaint at the show (`unmeasurable`; round 4: the record was spent under the zero layout, its numeric
   write a no-op on a zero-height scroller, and the note stood at its top once the pane showed; since round 5 the
   hide's own width report seats and lands nothing (its reflow still reaches the panel's hooks, whose trim Slice 4
   keys on it) and the show's seats the place read before the hide, or, over a scroll whose frame found the body with
   no box, the pane hidden in the scroll's own task, and marked it unread (`scrollUnread`), reads the offset the
   browser restored instead of seating over it, while the text and the width are the place's and the body is not back
   at 0 (an engine that restores no offset keeps the seat; round 6, a regression against ad612d193, whose cleared
   place had seated nothing: the repaint's seat moved the body back a frame's scroll, 100 px; boxless leg 4; since the
   review's closing pass the flag falls with the measurement it stands in for, a read of the place or a clamped seat's
   hold, and not with the repaint alone, since a flag set while the show's repaint stood down, the editor up or a
   media body shown, had stayed armed for a later show with no scroll behind it, which then read the block a clamped
   seat's landing showed in place of the held passage, place-memory case 11; and the restore is trusted only where it
   did not move the body: a scroll event since the hide's read, its own frame read still pending at the repaint, is
   the restore's, an exact restore firing none, and a restore that moved the body to below the place last measured
   seats the place instead, measured in headless Chromium, where the Raw view's restore lands short when the reader
   stood in the note's last 144 px at 900x520, a clamp against a layout pass shorter than the final one, and the
   Rendered view's is exact: the show had read the short offset as the reader's, 116 px short of a 30 px scroll into
   the end zone and 86 px behind the place before it, and dropped the hold a Raw swap from the Rendered view's end had
   taken, so the swap back landed four blocks off; a restore that moved the body to or past the place is read, the
   reader having scrolled at least that far, and a reader's own scroll in the frame between the show's layout and the
   repaint reads as the restore's; boxless leg 5), `notePlace` keeps the last measured place under a boxless body and
   the leave, `liveRecord`, writes it with its scrollTop, followed into the text a reload landed under the hide
   (`measuredPlace`: `followPlace`'s block, its neighbour's when the write rewrote it, as the seat steps; round 6: the
   Comments panel's poll landed a session's write under the hide and the pagehide wrote the old text's offset under
   the new mtime, a record that claimed exactness; boxless leg 3), and so, since the closing pass, is a clamped seat's
   held place at a visible leave (a reload's paint reads the place over the text before its swap and the seat holds it
   in the old text's terms when the new text ends at or near the reader's block, so the leave after it wrote the old
   text's span under the new mtime through `keptPlace`'s held arm, round 6's defect on the visible branch; `held`, the
   one test the seat's read and the leave share; place-memory case 10), so a restart's pagehide or a close under a
   hidden pane no longer keeps the previous leave's record on the row, and a Raw leave from an open holding a Rendered
   record's folds for a Rendered paint that never came carries them on, `heldFolds`, where the held state had died
   with the open); and files-recent.ts's `asPlace` accepts the field as a list of non-negative integers, anything else
   being no place. The brief's sentence for the Recent leg ("twenty paragraphs inserted above and reopen: block 40 is
   at the top again") contradicted that rule, so the leg asserts the same scrollTop with a different block there, and
   block 40 back within a pixel on an unchanged file and a file changed below it. The remembered seat does not hold a
   clamped write the way `seat(kept)` does (one seat path, one hold: a place at the file's end that the browser clamps
   reads back as the block the clamp shows), the recorded default, accepted by the PR review's round 1. Two follow-ups
   the review's round 2 recorded as
   not closable within the record's decided fields (spans, pixels and mtime, no text; open question 7) were closed in
   round 3, the fold state above being the one field added, each with a test red over a `git archive` of 27c56fbf7: a
   fold the reader had OPEN whose summary sat at or below the body's edge, or whose box started at or below it (the
   front matter at the note's top, an author's `<details>`, a `[!tip]+` callout the reader had closed coming back
   closed), came back as authored on the reopen, the content under the edge no longer showing, and the round 2 gate
   compared a pixel depth from the leave's width against the shut box at the reopen's width, a few-px window in which
   a wrapping title read open at 900 px and reopened at 380 came back shut; the record's folds close every face, the
   same block at the edge; and the numeric fallback after a page reload landed a picture's height off when a figure
   above the block loaded after the seat (round 2 measured 384 px, one figure; Chromium's scroll anchoring keeps the
   span path exact by moving the scrollTop, and an engine without it would show both paths a picture's height off):
   `armReseat` runs right after the remembered seat when a picture in the body has not loaded, and a capture-phase
   `load` listener on the body (an img's load does not bubble) writes the seat again at each picture's load while the
   body stands where the seat and the browser's own adjustment left it, the same scrollTop or the same top block at
   the same offset; a scroll of the reader's, the next text paint and the close retire it; no timer (the review's
   round 4 pins the scroll and the paint retires as behaviour in files-recent-place-browser's third leg; the close
   discards the body with the listener, so nothing of it can show, and it stays a source pin). The sentence above,
   that a changed width comes back near, not exact, stands. The Files pane persists the record on the Recent row:
   `RecentFile` gains `place`, a stored one is validated field by field on read (`asPlace`: a malformed record costs
   the place, never the row), `rememberRecent` keeps a row's place across a re-open that brings none (the viewer hands
   the pane the place of the file it LEAVES before the re-open's own row is written), `placeRecent` writes one on its
   row; files.ts wires `onLeave` to that write, and `openHere` reads the latest record among the rows that name the
   same FILE by the viewer's `placeKey` (an absolute or `~` path one file for every session, a relative one per
   session; files-recent.ts `latestPlace`) and hands it back through `opts.place` on every open of the file, the row's
   click or any other (the review's round 1: with the row's click alone handing it back, a chat click through the
   relay after a page reload opened the note at its top and its leave wrote that top over the row, the place lost for
   good; round 5: with the open's own row alone read, two sessions' rows for one absolute path landed at the file's
   latest place before a reload, the in-page memory's shared key, and each at its own older place after one, the same
   row landing differently by whether the page had reloaded; the record is read before the open, so a replace-open's
   leave, which rewrites a row during the open, is kept, the viewer seating the later of the two; the write stays per
   path and session, so the rows and the store's shape are unchanged); the JSON in localStorage holds the eight
   fields, and `folds` for a Rendered read of a note with a fold, and nothing else (`asPlace` drops any other field).
   The chat modal and the feed viewer persist nothing across a page load (open question 7's default); their in-page
   map covers a switch between files there. Cost: one `readPlace` per leave, one `placeRecent` map over at most eight
   rows and one JSON write per leave. Not built: the wrapper control the brief's routing (i) asked of the memory leg
   (the wrapper rulings stand through `readPlace`, unchanged, and the place legs ran green).
   file-view-place-memory.test.ts (13, new: the real openFileView over a stand-in that, unlike the seam's, has a
   layout, so the seat is read as a scrollTop; the two pure functions, a close and a reopen to the pixel with nothing
   scrolled into view, a host's record and the later `t`, a replace-open, a changed file in its four shapes, the views
   against each other, an `at` open, pagehide, the editor, a picture and a missing file, source pins on the three
   write sites and the seat's place; from the review's round 2, `placeKey`'s four shapes, two sessions' relative path
   as two files and an absolute path shared, and the editor's leave writing the pre-Edit place at pagehide and at the
   close; from round 3, case 6 pins the reader's own sequence, Edit saving the Raw preference, the un-cleared reopen
   painting Raw with block 12's first row at the edge, the Raw close's record and a Rendered reopen after that round
   trip seating the block at the edge, and two source pins moved with the record's fold field; in round 4 the replace
   path's pin admits the prior ring's read between the guard and the leave, and landRemembered's the boxless-body
   guard; in round 5 the `liveRecord` pin reads the boxless leave and `heldFolds`; in round 6 that pin re-aimed and
   one on `measuredPlace` added; in the closing pass case 10, the visible leave after a reload whose seat clamped,
   through the seam's reload from a probe action, and case 11, the unread-scroll flag under the editor (the eighth and
   the ninth until the PR review's round 1 inserted its two cases ahead of them), through a ResizeObserver stand-in
   the case reports through and the body's rects and width faked for the hide and the show, with the `liveRecord` pin
   re-aimed to `held`; in the PR review's round 1 case 7 extended with the three keys of a host-prefixed sid and a
   scene over the shared absolute path, the remote open landing at 0, its leave to 250 leaving the local's 330
   standing and each reopen its own, and two new cases, the URL viewer's replace path executed, a guard, red with
   `runLeave` removed from `openUrlView`, and a line, an offset, a heading and no target on a picture and on a PDF,
   the notice's words and role and the body holding the keyboard, red over a `git archive` of 3e433ceee),
   files.test.ts (16, two new over the pure half, the wiring pins re-aimed and one executed; from the review's round
   1, `openHere`'s body lifted and run over stubs: the relay's open, a link's and the row's click hand the record, an
   `at` open hands it too, a replace-open's fresher leave record stays on the row, a veto records nothing; the
   eight-field pins gain the fold field in round 3; in round 5 the executed case runs `placeKey` lifted from
   file-view.ts, another session's row for the same absolute path handing the file's record, of two rows for one file
   the later seating whichever row is clicked, another session's relative path or no row handing null, and one pure
   case over `latestPlace`; in the PR review's round 1 the executed case binds the lifted `placeKey` to the real
   `hostOf`, asserts a remote session's key and hands the remote open null and then its own row's record after its
   leave, red over a `git archive` of 3e433ceee), files-recent-place-shared-browser.test.ts (2 legs, new in the
   review's round 5: the real Files page in headless Chromium, two sessions reading one absolute path, the second's
   relay landing at the first's place, either row landing at the file's latest read before and after a page reload,
   the rows told apart by their session chips, a relative path keeping each session's own place across the reload, no
   word of the note in the store; red over a `git archive` of ad612d193 at the post-reload landing; a second leg in
   the PR review's round 1, the remote route served as another text, the remote session's relay landing at the top,
   the rows and chips per host, each row's landing its own before and after a page reload and no word of either note
   in the store, red over a `git archive` of 3e433ceee where the remote open landed at the local's 1489),
   files-recent-place-browser.test.ts (3 legs, new: the real Files page in headless Chromium, the acceptance reopen
   within a pixel, the record's JSON, a change below and above the block, a page reload with the shell's relay as the
   first open after it returning to the block and its close keeping the block on the row, a replace-open with two
   rows, a relay re-open through the viewer's in-page memory; from the review's round 3, a record read at Paragraph 65
   with a figure loaded, a page reload, the note changed above the passage (the numeric path), the figure held at the
   landing and released, the body ending at the record's scrollTop with an earlier block at that pixel, over an .svg
   the leg's route serves as image/svg+xml, never cached, held while the test says so, and from round 4 two figures
   held by path: after the first figure's re-seat the reader scrolls 400 px on and the second figure's load leaves the
   reader's block at the top with the record's number not written back, and after a second reload with five paragraphs
   inserted for twenty a Rendered/Raw round trip before the loads leaves the paint's own block at the top, the
   record's number again not written back, so the scroll and the next text paint retire the re-seat; the stored keys
   pin keeps its eight fields, its message since round 3 saying that a note with no fold records no fold state: this
   leg's note has no `<details>`, so the ninth key, `folds`, is pinned over a note with one in
   file-view-place-memory-fold-browser.test.ts, and in files.test.ts's JSON case; the round 3 commit message's clause
   that this leg's key pin gained the field is a slip and stands as history),
   file-view-place-memory-fold-browser.test.ts (13 legs, new in the review's round 1: at 900 and 380 px an authored
   `<details>` and a folded callout come back open with Paragraph 25 at the same edge and the scrollTop within a
   pixel, a fold the reader left shut stays shut with Paragraph 41 exact, and a Raw record reopened under the Rendered
   preference opens the fold with the block at the edge; from round 2, at both widths a shut callout 6 and 14 px above
   the edge and shut front matter 8 px above stay shut with the scrollTop and scrollHeight unchanged, the open callout
   read inside still comes back open, the open callout with its summary straddling comes back as authored with the
   same block at the edge, and an open at an offset inside a shut callout opens it with the passage shown inside the
   body's box; from round 3, at both widths a fold the reader had open with its box 12 px below the edge, the front
   matter opened at +3 with its `pre` shown again, an author's `<details>` at +12 and a `[!tip]+` callout the reader
   closed coming back closed, a wrapping title read open at 900 px and reopened at 380 back open with Paragraph 11
   under the edge, and the straddling open callout 6 px above back open with the same scrollHeight, the record's
   `folds` being [0] and its JSON holding no word of the note, the same leave under another mtime falling back to the
   round 2 rule; a Raw record inside a folded callout reopened under the Rendered preference with the callout open,
   its top at the edge and Paragraph 25 shown; and an offset in a comment right after a shut callout, and in the
   trailing blank line after a shut last callout, leaving the callout shut with Paragraph 41 inside the body's box;
   from round 4, four legs each red over a `git archive` of 7fbced030: a callout left shut at 380 px with the edge 50
   and 40 px into its two-line shut box, reopened at 900 px, staying shut with the shut layout's height, the 380 to
   380 control shut and round 3's face, read open at 900 and reopened at 380, still open; at both widths a Raw record
   at the file's very top with the front matter's block starting under the edge leaving the front matter and the
   callout shut on a Rendered reopen, a Raw record inside the front matter's rows and one with the callout's first row
   at the edge still opening the fold; at both widths the fold state held past a Raw first paint, via Edit and via a
   preference switch, the Rendered toggle showing the fold open with Paragraph 25 shown and the scrollTop back within
   a pixel, a Rendered reopen of the same leave restoring it exactly; and at 900 px a reopen painted under a hidden
   pane, the record pending until the show and Paragraph 40 back at the same edge, the visible control the same; from
   round 5, at both widths a Raw record read with the blank row before a shut callout at the edge and the callout's
   first row 4 and 12 px under it opening the callout on a Rendered reopen with Paragraph 11 shown, a forty-row
   comment before the callout with its first row at the edge, the record's block starting below the body's height,
   leaving it shut (a guard) and a five-row comment opening it, and at 900 px a Raw leave from a reopen whose Raw
   first paint held a Rendered record's folds carrying `folds` [0], the Rendered reopen putting the fold back open
   with Paragraph 60 at the edge; from round 6, at 900 px a Rendered read with the callout shut as authored, Edit and
   a close from the editor (folds []), a Raw reopen read into the callout's rows and closed (the Raw record's block
   the callout, folds [] carried on) and a Rendered reopen opening the callout with Paragraph 25 shown, and the same
   for the front matter with its `tags:` row at the edge, its text shown; 0/1 over a `git archive` of 85fa51bf5),
   file-view-place-svg-source.test.ts (1, the SVG Source branch's seat re-pinned).
4. *Item 4, the open-at target.* `openFileView(path, sid, { todoId?, at?, place? })` takes one target per open, the
   exported union `At = { line } | { offset } | { heading }`, in place of the `line` and `frag` options (replaced, not
   aliased: one shape for one thing, open question 10's default; `place` is item 3's record and not a target).
   `readAt` validates what crossed a frame boundary (a positive integer line, a non-negative integer offset, a
   non-empty heading, in that precedence when a message carries more than one arm; a non-integer number is no target;
   anything else opens the file at its top). A `{ line }` lands as `line` did: the Raw view for that open with the
   preference unsaved, the row centred once the text lands, the past-the-end notice. A `{ heading }` lands as `frag`
   did, one frame after the first Rendered paint through `scrollToFragment`, waiting for the Rendered toggle under the
   Raw preference of a markdown file, or, for a file that is not markdown, one frame after its first text paint, there
   being no Rendered toggle to wait for (the review's round 2: a todo's `src/app.py#l12`, the section spelling of a
   line slip, opened the file silently at its top, the target never spent), or, for a picture or a PDF, at its first
   paint with bytes (the review's round 3: `figs/a.svg#layer1` and `docs/report.pdf#page=3` opened silently at the
   top; the PDF viewer's own page grammar is outside the plan's scope, so `page=3` is a section the file lacks and the
   notice says so); a heading the file has no section for now says so in the notice bar (`No section named "X" in this
   file.`, the name percent-decoded where it decodes) where a silent open at the top read as the file's truth, and a
   heading the file has under a plain `hidden` wrapper, found but with no box to land on, says `That section is hidden
   in the rendered view; opened at the top.` (`HIDDEN_SECTION`, the words the PR review's round 1 gave:
   `scrollToFragment` answers false for such a target as for a missing one, one line after its lookup, and
   `spendHeading`'s frame tells the two apart through `sectionHidden`, the same lookup, before the missing-section
   branch; an in-body `#` link to a hidden heading lands nothing as before, its callers ignoring the answer;
   file-view-outline.test.ts's twelfth case, a `<div hidden>` around a heading opened at it, the exact words, role
   status and scrollTop 0, the shown heading beside it landing with no notice and a missing section keeping its own
   words, red over a `git archive` of 3e433ceee). `{ offset }` is new: spent at the first text landing like the line
   and scrolled one frame later, the heading landing's
   timing in both views (a departure from the brief, which had it inside the landing: the Rendered pairing reads the
   painted DOM, and one timing for both views lets the seam's stand-in lay the elements between the paint and the
   frame); in the Rendered view the block holding the offset (anchor-map's `sourceBlockSpans`, read as the reader's
   place reads them, paired to its element by `renderedBlockElements`; a block with no element of its own, a comment,
   stands aside for the nearest earlier block with one, then the nearest later; a fold above the target is opened
   first, and since the review's round 2 the block that IS a shut fold, a callout, is opened too, the offset naming
   content its summary hides, where `revealFragmentTarget` opens ancestors alone and the shut summary was centred over
   the hidden passage; the offset's OWN block only, since round 3: a stand-in for a block with no element, a comment
   right after a shut callout or the trailing blank line after a shut last one, leaves the callout as authored, the
   offset naming the comment and not the callout's content) scrolls to the centre, in the Raw view the row at the
   offset through the seam's own `scrollToOffset`; past the end of the text it lands on the last block or row and says
   so (`Offset <n> is past the end of this file, which has <m> characters; showing the last block.`, or `the last
   line` in Raw); a source with no blocks scrolls nothing and says nothing. Since the review's round 5 the line, the
   offset and the heading wait for a body with a box (`landTarget`, run at the landing and again from the width hook's
   repaint at the show; the heading's frame parks the target again under a boxless body, `spendHeading`), where a
   first text paint under a hidden pane (the pane's document `display:none` while the fetch was in flight) had spent
   them over the zero layout, `scrollIntoView` moving nothing and the landing counting as done, so the note stood at
   its top with no notice once the pane showed; and since the PR review's round 1 a picture's or a PDF's target waits
   the same way: `landMedia`, run from the blob landing and from the width hook's repaint over a media body, lands
   nothing under a body with no box (the text landing's `unmeasurable` guard) and otherwise names a line or an offset
   target in the notice bar in the heading target's shape (`spendOnMedia`: `No line 12 in this file: it is a
   picture.`, `No offset 1200 in this file: it is a PDF.`, the heading's words as before; the words are the build's,
   the round having given none) and spends the one-shot keyboard take, where the build had spent the heading alone at
   the media paint, dropped a line or an offset on a picture or a PDF in silence, the text arm being their only
   spender, and spent the take without the guard, so under a hidden pane nothing held the keyboard at the show
   (file-view-place-memory.test.ts's picture-and-PDF case and file-view-boxless-browser.test.ts's sixth leg, an SVG
   served as image/svg+xml opened at a line and an offset, visible and hidden at the paint, no notice under the hide
   and at the show the notice and the body holding the keyboard; both red over a `git archive` of 3e433ceee). The
   relay carries the target as `at` at every hop,
   since the shell rebuilds the message field by field and a field not copied is dropped: render.ts's `openPath(path,
   sid, ev, at)` posts it and hands it to `openFileClick`'s new fifth argument for an in-document open; waiting.ts's
   `openTodoPath` posts it with `todoId`; kernel.py's two forwarders copy `at:m.at||null` (the Files branch and the
   feed branch; the pane branch's comment defines the field); `initFileView`'s default branch opens `{ at:
   readAt(m.at) }` and the Files pane's `onRelay` reads it through the same `readAt`; `host.openFile` becomes `(path,
   sid, at)`, the body's delegate handing a path link's `data-line` as `{ line }` and its `data-frag` as `{ heading
   }`, the two attributes it read before. The producers: path-links.ts gains the `targetSuffix` walk option beside
   `lineSuffix`: the `:line` grammar `lineSuffix` reads (`LINE_SUFFIX_RE`: `:12`, `:12:4` with the column dropped,
   `#L12`, `#L12-L20` keeping the first line) into `data-line`, and one more arm, the section (`FRAG_SUFFIX_RE`, `#`
   then one or more characters that are not whitespace or `#`, not beginning `L` and a digit, so `#L12` stays a line,
   `#L12abc` stays prose and `#l12` is a section; the name percent-decoded where it decodes, trailing sentence
   punctuation left to the prose, a URI's swallowed tail cut back out, the section's tail before the line's since the
   PR review's round 1: both cuts anchor at the token's end, so `file:///repo/notes-api/docs/a.md:12#results` had kept
   `:12` in its path and carried the section as `data-frag`, and now links the file at line 12 with `#results` left to
   the prose, as after the bare `docs/a.md:12#results`; the chat's default walk and the viewer's `lineSuffix` walk
   never cut a section and are unchanged in behaviour, the `lineSuffix` follow-up recorded below standing) into
   `data-frag`; the link's shown text grows
   by the suffix, and a suffix a highlight span cuts is refused as the line is. `linkTarget` reads the two attributes
   back as `{ line }` or `{ heading }`, one reader for the hosts, an `At` by structure so neither render.ts nor
   waiting.ts imports the viewer. render.ts's two todo walks (the card's line, the detail) and waiting.ts's run under
   the option, spelled inline at each site since the tests lift those functions and run them as written; the chat
   transcript's own walk is unchanged, its kernel verdict being on the bare path (open question 11, the default), and
   a todo's structured `file` field stays a bare path (the kernel stores and matches it by realpath). The VS Code
   host's `openFile` arm receives `line` for a line target, which it already honoured and no sender fed; a heading or
   an offset posts nothing extra (open question 15, the default; nothing under vscode-extension/src changed).
   Measured: a todo link's heading lands with its top 9.5 px under the body's edge, the sheets' 10 px
   `scroll-margin-top`, the bound md-config-fragment-landing-browser reads (`<= 12`), not the brief's "within a pixel"
   of the edge. Edges recorded: the conflict bar's "Reload file" re-open passes the open's options as before, so an
   `at` target lands again on that re-open, as `line` and `frag` did; `readAt` refuses `{ line: 1.5 }` where the
   in-process option floors it (the relay's producers write integers, so the two never disagree in practice). The two
   shell lines are JavaScript the kernel SERVES, not Python it runs, so no kernel behaviour changes for this item
   (item 5's 404 reason header, the PR review's round 2, is the slice's one change to the kernel's Python and deploys
   with them); the live dashboard picks the field up only when the live kernel restarts after the landing, and until
   then a todo link routed to the Files pane opens the file at its top. Cost: one sticky regex per linked token on the
   todo surfaces (`FRAG_SUFFIX_AT_RE`, read in place, never a slice of the text). file-view-seam.test.ts (39, five new
   here: `readAt`'s arms and refusals; a line, a heading and a malformed `at` through the relay's default branch and
   the body's delegate; the missing heading's notice and the landing held for the Rendered toggle; the offset on the
   block and on the row, past the end with the notice; from the review's round 2, a heading target on a file that is
   not markdown judged at its first text paint, the notice naming the section decoded and nothing scrolled, a note's
   Raw view still waiting for the toggle; the stand-in records `scrollIntoView`'s argument and runs a per-case
   animation-frame queue), file-view.test.ts (53, four new source pins, this item's over the union, `readAt`, the
   spend and the frame, the two notices and the Rendered path, item 5's, from the review's round 2 one over the
   round's shapes, the peer-frame read, `placeKey`, the catch's closer, the non-markdown spend, `editPlace` and the
   two fold rules, and from round 3 one over that round's, the record's `folds` with `openFoldOrdinals`,
   `restoreFolds` and `armReseat`, the media branch's heading spend, `underHidden`, the rows' ids and
   `aria-activedescendant`, the Tab branch, the `select`, the offset's own-block gate, `raiseHold` and the re-arm
   after the pane's paint, item 5's pin gaining `takeKeyboard`'s `focusVisible`, `ringOf`, the Outline closer's read
   and the Reload's record; six re-pinned for the signatures, the relay and render.ts's `openPath`; in round 5 pins
   re-aimed to `landTarget`, `spendHeading`, the repaint line, `parkedLanding`, `liveRecord` and the fold rule's flag;
   in round 6 to the raise's go line, the fold rule's arm, the repaint and the reader-place import; in the PR review's
   round 1 one new over that round's shapes, the bar's words read off the HEAD's verdict, `landMedia` and
   `spendOnMedia`, `retakeAfterHide` with its two listeners and two call sites, `HIDDEN_SECTION`, `sectionHidden` and
   `spendHeading`'s order, the `on` class put on before the popover's box is read and the notice bar's role, and the
   pins re-aimed to `pressHold(box)` and the host in `placeKey`), file-view-boxless-browser.test.ts (7 legs, new in
   the review's round 5: in the pane at 900 px an open at a heading,
   a line and an offset painted under a hidden overlay, the file GET held while the hide comes, lands its target with
   no notice once the overlay shows, the heading's top at the edge less its scroll margin, the row and the block
   inside the body's box, and the body holds the keyboard with PageDown scrolling, the visible control landing the
   same; a leave under the hidden overlay, the page's pagehide and a close, writes Paragraph 80's block with the
   scrollTop as last measured, and the reopen after the show returns to it; 0/2 over a `git archive` of ad612d193; two
   in round 6, item 3's: a reload landing under the hide, the seam's reload as the panel's poll calls it, then the
   pagehide and a close writing Paragraph 80's block in the text that landed, at its mtime, with the depth as read,
   the reopen returning to it and the visible control writing the same span; and a scroll in the task of the hide,
   whose frame found no box, kept at the show, the body 100 px on where the browser restored it and a 1 px reflow
   keeping the block the scroll put at the edge, the control with the scroll three frames before the hide landing the
   same; 0/2 over a `git archive` of 85fa51bf5; one in the closing pass, item 3's: the hold a clamped Raw seat took
   from the Rendered view's end surviving a hide in the seat's own scroll event, the body at the Raw view's end after
   the show and the swap back landing the block the reader had at the edge, a 30 px scroll into the Raw end zone with
   the hide in its task coming back no further behind than the place a frame before it, and the controls, the hide
   three frames after the swap, the scroll three frames before the hide and the Rendered end zone, exact; 0/1 over a
   `git archive` of 14a246665; two in the PR review's round 1, item 4's picture opened at a line and an offset under
   the hide and item 1's pane toggled off and on re-taking the keyboard at the show; 5/7 over a `git archive` of
   3e433ceee), path-links.test.ts (15, five new: the grammar's spellings, the controls with the default and
   `lineSuffix` walks unchanged, a section a highlight span cuts, `linkTarget`, and from the PR review's round 1 a
   file URI carrying both a line and a section, held to the bare form, the controls case gaining the both-tails URI
   under the default and `lineSuffix` walks),
   render-open-path-target.test.ts (5, new: `openPath` and `openLinkedPath` lifted and executed for the in-document
   route, the pane relay and the host's `line`; the window stand-in's projection, added by the consolidation pass when
   the full npm test's shim ratchet named the file), user-todo-links.test.ts (12, the executed payload gains `at` with
   a heading and a line case, the pins moved), waiting-detail-link.test.ts (5, one new: a heading, a line and a bare
   path through the real matcher and both lifted delegates), todo-link-target-browser.test.ts (2 legs, new:
   render.ts's own lifted handlers over the Files bundle land the heading at the edge, open the Raw row, name a
   missing section and open a bare path at the top; framed with the pane preference the relay carries `at`),
   waiting-file-chip.test.ts (12, the posted shape gains `at: null`), tests/test_files_pane.py (24, one new over both
   forwarders and the receiver, three literals re-aimed), and source-pin re-aims for the moved shapes in
   file-view-links, md-url-view, pdf-new-tab, user-todo-title-links, url-links, file-uri-link, chat-space-paths,
   user-img-dedup, render-todo-file-chip, waiting-link-focus, waiting-pane-browser and chat-relpath-link tests, and,
   found by the full npm test in the consolidation pass, chat-path-links (the transcript's `linkifyPathTokens` call
   with `walkOpts`), chat-pin-history (`linkifyFileUris`'s signature) and vscode-extension/src/chat-focus-model (the
   key handler's slice widened past the arrow branch's stand-aside) tests.
5. *Item 5, the changed-on-disk line.* With the Comments panel closed nothing watched a shown file. The viewer now
   runs one `HEAD /file` of the URL its GET used on two events of the host document, a `focus` on the window and a
   `visibilitychange` to visible, while it shows a fetched file (text or media, `mtimeNs` set: open question 13's
   default, with one clause added, that the document is visible, so a focus while hidden asks nothing), the editor is
   down and no HEAD is out (a second event while one is out is folded into it; no timer anywhere: the events are the
   reader's return, the answer and the landing). The answer is read as the panel's poll reads its own, `headVerdict`
   then `mtimeMoved` from file-comments-model.ts imported as they are (a string compare, the contract the panel and
   the save fence keep); the poll and its `stopped` set are untouched, and the poll's header in file-comments.ts says
   the pane has no filesystem watcher, true of the panel, and since the consolidation pass adds that with the panel
   closed the viewer's own probe reads the same header through the model's two functions and never writes the mtime
   (the clause the brief's item 6 asked for; a comment, no code of the module changed; routing (h): the readings are
   the model's, the poll the panel's, the probe the viewer's). A 413 or 415 retires the probe for the open; a network
   failure paints nothing and says nothing; the listeners are dropped by both exits and the URL viewer's replace. A
   moved mtime raises the one-line bar above the body row through `noteBar`, `Changed on disk.` (exported as
   `CHANGED_ON_DISK` for the pins), or `Deleted on disk.` (`DELETED_ON_DISK`) when the HEAD answered 404 with the
   kernel's one-word cause `missing`, the words read at the answer off the verdict (`headVerdict`'s absent) and off
   the 404's `X-Romp-Reason` header (the exported `REASON_HEADER` and `REASON_MISSING`: `missing` is a file gone from
   its absolute or `~`-rooted path, and any other cause, `relative` for a path the session's cwd moved from under,
   `unresolved` for one with no cwd to join, `detached` for a remote host with no tunnel, or no header at all, a
   kernel from before it, keeps the change's words, Reload then painting the kernel's own pane for what the GET
   answers; the PR review's round 2, the Manager review round 2 paragraph below) and kept on the bar's record so the
   editor's exit re-raises the words the bar had (the PR review's round 1 ruled a 404 a deletion, not a change; its
   round 2 narrowed the reading to the cause the kernel certifies), with a `Reload` button on the words' line
   (`.fileview-err-act` in both sheets, in the parity list; the review's round 5: dressed as the refusal pane's block
   Download, `.fileview-err-dl`, the bar was two rows and 89 px tall at every width) whose title says the place is
   kept, the raise waiting out a press on the body row, `.fileview-main`, the body and the Comments aside, through a
   hold of its own (`raiseHold`, a `pressHold(main)` beside the landing's on the body, which parks one run at a time,
   and a raise must never displace a parked landing; the review's round 3: the mousedown that begins a drag in a Files
   iframe that did not hold the page's focus is itself the window focus that runs the HEAD, and the bar is a row of
   the card above the body, so a raise while the pointer was down moved the body under the press and the drag's
   selection ended on other text, the composer quoting the wrong passage with the Comments panel open; the guards
   re-run at the release, and a landing parked under the same press runs first and stands the raise down, since round
   5 by the raise waiting for that landing's settle (`parkedLanding`, recorded by `fetchFile`'s `land` while the
   body's hold is held: the row's hold hears the press before the body's, both listening in the capture phase, so its
   parked run went on the zero timer first and inserted a bar over the old mtime that the landing's settle removed a
   task later; since the PR review's round 1 the landing's hold is the card's, `pressHold(box)`, item 2's fix, whose
   listener hears a press before the row's, so the order holds by the settle and not by which hold hears the press
   first), the raise's guard at the release being, since round 6, that the body still shows the file the HEAD compared
   against (`was`, the mtime at the answer), any landing since making the HEAD's evidence stale whatever mtime it
   brought (round 6: a parked landing that brought a second write, newer than the HEAD's answer, read as moved against
   that answer and raised a false bar over the newest file, standing until Reload, 3/3 on 85fa51bf5 and on 7fbced030,
   masked on ad612d193 by the flipped order; a departure recorded: a parked landing that brought an OLDER mtime than
   the HEAD saw, a GET served before the write the HEAD saw, stands the raise down too, the body showing a file the
   disk moved past with no line until the next focus HEAD raises it over the file that shows, and with the Comments
   panel open, the one source of a parked landing, its poll re-asks within its interval; reload case 20 pins both
   faces); round 4: held on the body alone, a press on a card's head or a drag in the reply box in the aside while the
   HEAD landed had the bar land under it, the control moved out from under the pointer, the click lost and the drag
   selecting nothing); the click disables and relabels it `Reloading` and runs `fetchFile`, so the reader's place is
   kept as every reload keeps it and the landing runs through the body's press hold as every landing does. The bar
   goes at the landing that applies a different mtime from the one it was raised under, whoever asked for that reload
   (with the panel open its poll asks within 2.5 s and the later landing rules; open question 14's default), OR at the
   landing of the bar's own ask, or of any fetch newer than it (`ownAsk`, since the review's round 2), whatever mtime
   it brings (a departure from the brief, which named the different-mtime landing alone: a HEAD answered after a newer
   landing had already put the moved file in the body raised it over the file that shows, and without this rule that
   bar stood with a disabled button; a numeric mtime compare in the probe is the alternative for the review); a
   landing under the same mtime by another ask keeps it (a GET out before the write); the bar's own ask failing, or
   any fetch newer than it (the 404, 413 or 415 pane, a network failure), re-arms the button above the pane so the bar
   is no dead end (a second departure; removing the bar over the pane would leave a transient failure with no retry;
   the review's round 2 widened the clearing and the re-arm from the bar's own ask to any fetch newer than it,
   `ownAsk`: `fetchSeq` is monotonic and `fetchFile` drops a landing a newer fetch overtook, so once the Comments
   panel's poll asks its own reload during the bar's flight that newer fetch's bytes or failure are the bar's answer;
   before, the poll's GET after a deletion met the 404 pane and the bar stood over it with its button disabled at
   Reloading for the rest of the open, every later focus HEAD returning on the standing bar). One bar: a second move
   while it stands replaces nothing. A later one-line notice (the Edit refusal under an edit block, a refused save, a
   comments-log warning) takes the bar's row, `noteBar` keeping one notice, and nothing re-raises it while the reader
   stays in the tab, the probe firing on the window's focus and the document's visibility alone; the next event's HEAD
   raises it again and replaces the later notice in turn (the review's round 6, measured through the real bundle: the
   refusal stood through scrolls, clicks, keys and a resize, and a dispatched focus brought the bar back); the guide
   states the one-bar rule; whether the bar should outrank other notices is a design call for a follow-up, recorded in
   item 6. Since the PR review's round 1 `noteBar`'s div carries `role="status"`, a polite live region, set right
   after the insert so styles-fileview-err-sizes' contiguous-lines pin stands, and every notice announces itself to
   assistive technology, the changed-on-disk bar being the one raised with no gesture of the reader's
   (file-view-reload.test.ts's first changed-on-disk case and file-view-notebar-browser.test.ts's third leg, per cell,
   red over a `git archive` of 3e433ceee, the role null; the media and hidden-section cases assert it too).
   The bar's raise or drop changes the body's height, and with the Comments panel open the panel's body size report
   (the `ResizeObserver` its `installLayout` arms for every layout) re-runs the Comment float's subject test as the
   body's scroll and a figure's load do, so a float offered beside a standing selection hides when the passage moves
   under the bar, the selection standing and the next mouseup offering it again (the review's round 5: the button
   stood 117 px above the passage, over other text, until a scroll; a comments regression in the Rendered view under
   the owner's standing rule). While editing the probe stands down and the editor's entry takes the bar with the other
   notices; Cancel brings both back, the bar at the exit itself and without a HEAD (the review's round 1: `exitEdit`
   re-raises it when no re-read is pending and the file that shows is still the one it was raised under, the mtime
   shown being `diskBar.under`; a save that landed moved the mtime, and a fetch the editor held lands and settles it
   itself; before that the old text stood with no line above it until the next focus). Edges recorded: a deleted
   file's HEAD answers 404 with the reason `missing`, which `headVerdict` reads as absent and `mtimeMoved` as moved,
   so the bar says `Deleted on disk.` and Reload paints the 404 pane in the body, no Download offered, the bar
   standing with its button re-armed, a second HEAD replacing nothing and the file back on disk clearing it at the own
   ask's landing, the one-bar rule unchanged (the PR review's round 1; the build had said `Changed on disk.` for a
   deletion, loose words under the one-bar rule, and no case sent the probe a 404; since its round 2 the reading is
   narrowed by the reason header, reload case 13 models the kernel's `missing` and case 21 the other causes); a window
   `focus` fires only on the window holding the focus, so an alt-tab return to a tab whose Files iframe does not hold
   it sends no HEAD from that iframe (`visibilitychange` fires in every frame on a tab switch; item 1's body focus
   makes the iframe the holder in the common case); a real `page.bringToFront` fires no window focus event in headless
   Chromium (measured: `hasFocus()` true throughout, no event, no HEAD), so the leg dispatches the event the browser
   would. The kernel's HEAD route answers as before but for one header since the PR review's round 2: its 404 names
   its cause in one word, `X-Romp-Reason`, which the probe reads (the Manager review round 2 paragraph below), the
   slice's one change to the kernel's Python (four words since the PR review's round 3, its paragraph below), held by
   tests/test_kernel_preview.py (29, six 404 reason cases) and tests/test_kernel_remote_file_relay.py (20, five relay
   reason cases). Cost: one HEAD per focus or visibility event
   (`window.__heads` in the harness), zero repaints and zero GETs until Reload, one GET and one repaint for the
   Reload; an open into a Files iframe that did not hold the page's focus costs one GET and no HEAD (the review's
   round 1: the body's own `focus()` fires the window's focus event synchronously inside it, and the probe read that
   as the reader's return, GET then HEAD on every cross-frame open; `takeKeyboard` now marks its call and the probe
   stands aside for it). file-view-reload.test.ts (22, ten new in the build: the stand-in's fetch stub answers a HEAD,
   held, failed or 413 on request, and the document dispatches its own events; the focus's one HEAD and no bar under
   the same mtime, the moved mtime's bar as a card row with its words and button and no bytes fetched, hidden asking
   nothing and visible asking once, the in-flight fold and the network failure, the 413 retire and a fresh probe on a
   replace-open, the Reload's acknowledgement, one GET, the landing clearing the bar with one repaint and no scroll, a
   same-mtime landing keeping it, editing and the editor's entry, the close removing the listeners, a picture probing
   and a 404 pane never, the own-ask clearing and the failed Reload's re-armed button, and the Reload's keyboard, from
   the consolidation pass and corrected by the review's round 1: the click's record hands it to the body at the
   landing (the stand-in's `disabled` setter drops the focus as a browser does, so the case fails before at the drop
   itself), the panel's box keeps it through the poll's clearing, a failed Reload puts it back on the re-armed button
   while nothing holds it (the review's round 2: a box the reader moved to during the failed flight keeps it); the
   stand-in gained the browser's focus fixup for a removed subtree; from the review's round 1, Cancel bringing the bar
   back at once with the HEAD count unchanged; and, from round 2, the bar's ask overtaken by the panel's reload: the
   newer fetch's 404 re-arming the button over its pane, the overtaken GET's late answer changing nothing, the
   re-armed click landing the file back, and a newer landing of the moved file clearing the bar; from round 3, a
   failed Reload's re-arm after the pane's paint with a code element inside the body focused mid-flight, the re-armed
   button holding the keyboard and the box-keeps-it rule re-asserted, and the raise parked under a pointer press on
   the body, the HEAD's answer raising nothing, the release raising it through the hold's flush, a landing parked
   under the same press running first and standing the raise down, a press on the bar holding nothing; the case
   extended in round 4 with an aside mounted through the seam, a pointerdown on a card's head parking the raise until
   the release and no second HEAD, and in round 5 with a count of the bar's insertions across the release, zero, where
   the flipped order had inserted one over the old mtime; case 20 (the 19th until the PR review's round 1 put its 404
   case ahead of it) in round 6: a HEAD answering MT2 under the press and a landing bringing MT3 parked under it, no
   bar and none inserted at the release, the next HEAD raising nothing; and the trade, a GET served under MT4 parked,
   a write to MT5 the HEAD sees, no bar at the release and the next focus HEAD raising it, Reload clearing it; 18/19
   over a `git archive` of 85fa51bf5; in the PR review's round 1 case 6 asserts the bar's role and case 13 is new, a
   HEAD answering 404: one HEAD, the deletion's words, Reload painting the 404 pane in the body with no Download
   offer, the bar standing with its button re-armed, a second HEAD replacing nothing and the file back on disk
   clearing it at the own ask's landing; 18/20 over a `git archive` of 3e433ceee; in the PR review's round 2 cases 21
   and 22, appended: the fake's 404 carries the kernel's reason from a per-path table, a path with no entry answering
   `missing` as the kernel does for an absolute path; a relative path's `relative` raises `Changed on disk.` and
   Reload paints the kernel's pane naming the resolved path with the bar re-armed, a `TESTHOST`-prefixed sid fetches
   through `/remote/TESTHOST/file` and its `detached` 404 raises the same with Reload painting the no-attached-host
   pane, a 404 with no header, a kernel from before it, raises the same, and `missing` raises `Deleted on disk.` (case
   21, red over a `git archive` of e6aeb1138 with the deletion's words where the change's were expected); and the
   deletion's words across the editor, the bar up, Edit taking it, Cancel bringing it back reading exactly `Deleted on
   disk.` with Reload armed, role status, no HEAD sent and the keyboard on the body, and Reload then painting the 404
   pane with the bar standing (case 22, green over that archive and at the head, red under a mutation of the exit's
   re-raise to the change's words); 21/22 over the archive of e6aeb1138), file-view-notebar-browser.test.ts (9 legs,
   one new in the build: the pane at 700 and 380 px and the chat modal, the moved mtime's bar at scrollTop 400 above
   the body row with no repaint, Reload keeping the top block and clearing the bar, the panel's poll clearing it with
   the top block kept; one re-aimed, its past-the-end line passed as `{ at: { line: 9999 } }`; three from the review's
   round 1: at pane 700 and chat 700 a mouse Reload and an Enter Reload each leave the body active with PageDown
   scrolling and a failed Reload re-arms the button with the keyboard on it; after Cancel the body is active, the bar
   is back with no HEAD and the mtime unchanged; a shell stand-in holding a chat iframe and the Files iframe, the
   relayed open from the chat frame's body or a focused control there taking the keyboard across the frames with the
   GET and no HEAD and a dispatched window focus then sending exactly one, and from the composer, a text input or a
   contenteditable there leaving the keyboard in the box with the next keystroke landing in it, a click on the body
   then taking it and asking once (the review's round 2 restructured the round 1 leg into six holder cells; round 3
   added a `select` cell, focused and not clicked since a click opens Chromium's native picker, the body not taking
   the keyboard across the relayed open and the next keystroke being the dropdown's type-ahead, and one leg for a
   heading target on a picture, `figs/a.svg#layer1` served as image/svg+xml in the pane and the chat modal, the notice
   above the picture and none for an open with no target; two new in round 5: at pane 300 and 700 px and the chat
   modal at 380 the bar is one line, its Reload sharing the words' line, the bar under 70 px tall and the body row
   moved down by the bar's height, and at pane 800 px with the real panel open and a selection's Comment float
   offered, the bar's raise moves the passage and hides the float with the selection standing; both red over a `git
   archive` of ad612d193; the third leg reads the bar's role per cell since the PR review's round 1, 8/9 over a `git
   archive` of 3e433ceee)); real-viewer-leg.ts's fetch stub answers a HEAD with the GET's headers and no body and
   counts them beside `__fetches`.
6. *Item 6, the records, and what the earlier slices routed here.* docs/guide.md: the Files section's opening
   paragraph says a file reopened from the Recent list opens at the place it was left (the folder lines above the
   clause keep their hard wraps byte for byte; tests/test_files_pane.py reads them raw); "Your place in the file" says
   the file takes the keyboard when it opens, so the arrow keys, PageDown and Space scroll it at once, a box being
   typed in keeping it, and that a change on disk with the panel closed raises a line above the text on the reader's
   return to the dashboard, whose Reload keeps the place (the paragraph's rule for where a notice sits covers the
   bar); "How a markdown file reads" says the Outline button lists the file's headings and a pick scrolls one to the
   top, opening a closed fold around it; "Links in a file" says a line or a section after a path in a todo's text or
   detail opens the file there and a missing section is named in a notice, and, since the review's round 3, that
   Markdown read in Raw opens at its top and lands on the section, or shows the notice, once Rendered is clicked, the
   Raw view having no sections (round 2 had recorded the notice sentence as holding as written, false for a markdown
   file under the Raw preference, whose target waits for the toggle by item 4's design); and Waiting on you says the
   same of the pane's links, with the same Raw parenthetical, placed before the chip sentence another pin reads. The
   PR review's rounds 1 and 2 changed no guide sentence: none of the words they ruled appears in the guide, whose
   changed-on-disk sentence says a line above the text says so and quotes no words, so a deletion's line, and the
   change's words a 404 for another cause falls back to, are covered as written, and the hard-wrapped lines
   tests/test_files_pane.py reads stand byte for byte. tests/test_guide_files_place_and_outline.py (14, new; two in
   round 3: the Raw clause and the parenthetical in their places, and `renderBody`'s heading gate with seam case 38's
   three assertion messages, so the guide and the code cannot drift apart unnoticed; in the PR review's round 1 the
   disk-bar pin reads `noteBar(words)`, the deletion's export and the line that reads the words off the verdict, red
   over a `git archive` of 3e433ceee; in its round 2 that pin reads the words line with the reason header's read and
   the two exported constants, red over a `git archive` of e6aeb1138) pins the six clauses flattened, their places
   among the sentences around them, the clauses other pins read in the same paragraphs, and each against the source
   that keeps it. tests/test_reference_todo_file.py (20, two source pins re-aimed at the todo walks under
   `targetSuffix`, which item 4 moved and no test run of the build read). The comments in code that stated the old
   boundary are reworded: file-view.ts's options doc and the `pendingLine`, `pendingHeading` and `pendingOffset`
   comments name `at`; `initFileView`'s header lists the relay's `at`; files.ts's `openHere` doc carries `at` and
   `place`; files-recent.ts's header names what a row holds; kernel.py's relay comment defines `at`;
   file-comments.ts's poll header says the viewer probes on the window's focus with the panel closed (the
   consolidation pass; the module's code is untouched). CONTEXT.md is unchanged: the build coined no term (no reviewer
   asked for "remembered place"), and the PR review's rounds 1, 2 and 3 coined none. The ledger entry is
   upstream/2026-09-13-markdown-viewer-slice6.md (tier feature; its `where:` line names every file the branch changes
   and says the two shell lines need the live kernel's restart; since the PR review's round 1 it also names upstream's
   twin of the relay's field and the mapping between the two, the rule the offer and the next inbound fold apply,
   stated in the Manager review round 1 paragraph below; since its round 2 it names the /file 404's reason header, the
   served route's one Python change, deployed by the same restart, and ui/test-dom-shim.test.ts, which round 1 changed
   and its `where:` line had missed; since its round 3 it names the fourth reason word, `unreadable`, the narrowed
   `missing` and the relay's status guard, and cites the round 1 path-links case by the file's ordinal, case 12). The
   brief's open questions, each taken as recorded above: 1 the stacked base
   (the alternative, the coordinating session's call); 2 the label `Outline` with "the file's headings" in the guide;
   3 every heading as the DOM shows it; 4 the button in Rendered only; 5 the focus rule's reach, with the key-driven
   text-size step as the one exception; 6 the ring; 7 the record's fields, the path key, the page-life map and the
   Recent entry as the one store; 8 the span-start match and the clamped scrollTop; 9 an explicit target wins and the
   memory still writes; 10 one `At` union and a separate `place`; 11 a target after a path in a todo's text or detail
   and inside a shown file, not in the transcript or the structured field; 12 the caret-to-offset export not built; 13
   text and media, the document visible; 14 the probe runs beside the poll, the later landing ruling, plus the own-ask
   rule; 15 `line` alone to the VS Code host; 16 the button's place in the bar; 17 the numbers above (about 9 ms for
   500 headings, one parse per leave, one HEAD per event). What the earlier slices routed here: (a) the keyboard
   dropping to the document's body after a save or a Send (slice1-build.md:303, "viewer focus is Slice 6's") is closed
   as far as the viewer's half goes, the body taking the keyboard at the open and after its own gestures; a focus the
   panel drops (a `focusout` with no relatedTarget) is not caught, since the panel's own focus bookkeeping runs on the
   same events and a catcher would race it, and the suggested forward for the panel (a saved comment handing the
   keyboard to the new card's head or the Comment control) stays the panel owner's, and a Comment float the reader
   Tabbed onto, which the panel's own hide drops the same way (at the changed-on-disk bar's raise since round 5, at
   its poll's landing on every tree), is recorded below with the Tab-focused highlight, the same drop (the review's
   round 6); (b) the caret-to-offset export the Slice 2 record wanted and the Slice 8 note's routing sentence named
   ("which Slice 6 or a follow-up could add"; the PR review's round 1 ruled that clause "a follow-up" alone, and the
   Slice 8 note reads so) is not built: the memory seats a block, the Outline lands an element and `offset` lands a
   block or a row, so it is a follow-up of the reader's place and of no slice; (c) the keyboard selection offer is
   unchanged and its legs ran as controls; (d) the front-matter block mints no id and has no Outline row; (e) the note
   bar is Slice 2's bar and its leg is that leg extended; (f) the landing hold is inherited by the Reload and the
   initial seat; (g) the place is read once per leave; (h) the two readings are the model's, the poll the panel's, the
   probe the viewer's; (i) the wrapper control was not added to the memory leg (item 3); (j) Slice 7's failure paths,
   the VS Code host and the raw HTML `<table>` stay where they were. Edges the units recorded and the consolidation
   pass closed, each with a test that failed before it: render.ts's arrow shortcut scrolling the transcript with the
   viewer up, and the disk bar's Reload taking no keyboard (item 1). The review's round 1 (2026-09-13) closed, each
   with a test red over an archive of d91f0c19d: the arrow stand-aside ahead of both branches and the Reload's
   keyboard read at the click (item 1, the two consolidation fixes corrected), the editor's exits taking the keyboard
   (item 1), the Outline's closers handing it over, the popover placed from its containing block and anchored inside
   the card, the image-only row, the failure pane hiding the button and the open dress scoped to the Outline button
   (item 2), the remembered seat opening folds and the Recent row's place handed back on every open (item 3), the bar
   back at Cancel and no HEAD from the viewer's own focus call (item 5); and the records: this note's base sentence,
   the ledger's `where:` line and the build-process names defined at the head. The review's round 2 (2026-09-13)
   closed, each with a test red over a `git archive` of c88444f85: the keyboard rule reaching a typing box in the
   sibling frame through the top window (`typingInPeerFrame`), so a relayed open, a Reload's landing and a Save's ack
   leave the chat composer holding the keyboard, and the failed Reload's re-arm refocusing its button only while
   nothing holds it (item 1; round 1 had recorded the relayed-open take as the slice's design, reversed here: no relay
   field, the landing reads the focused frame); the failure pane's paint closing an open Outline popover, and a
   record, both sheets' Outline comment, the parity list's comment and two test messages saying the card was the
   popover's containing block, corrected to its `offsetParent`, the overlay, with a pin over both sheets (item 2); the
   memory keyed by `placeKey`, the editor's leave writing the pre-Edit place, and the block's own fold opened only for
   a depth past its shut box (item 3); a heading target on a file that is not markdown judged at its first text paint,
   and an offset inside a shut callout opening it (item 4); the bar's clearing and re-arm answering any fetch newer
   than its ask (item 5); and the records, the head's sentence on the three commit messages' identity claims, checked
   against the history by tests/test_markdown_viewer_plan_note_history.py (the module reads git as well as the note,
   so its three red cases ran over the note as committed at c88444f85 with the branch's history reachable; over a bare
   archive it skips). Round 2's fix commit, 27c56fbf7, names Seam case 39 for the heading target on a file that is not
   markdown; the case is 38, the 38th `test(` of file-view-seam.test.ts and `ok 38` in the file's run (`not ok 38`
   over the c88444f85 archive), and case 39 is the build's source-offset landing, moved from 38 by the new case's
   insertion ahead of it; the message stands as written, the history never rewritten (the review's round 3). The
   review's round 3 (2026-09-13) closed, each with a test red over a `git archive` of 27c56fbf7: the record's fold
   state, restored before the seat at the record's mtime, which closes round 2's two follow-ups and the width window
   of the depth gate, the re-seat at each picture's load, and a Raw record inside a folded callout opening it under
   the Rendered preference (item 3); the failed Reload's re-arm after the pane's paint, the `select` as a typing
   target and the ring named through `focusVisible` (item 1); the Outline's hidden heading, the rows' ids with
   `aria-activedescendant`, the alt text read in place and Tab handing the keyboard to the button (item 2); the
   offset's own block alone opening a shut callout, and a heading target on a picture or a PDF judged at its first
   paint with bytes (item 4); the bar's raise waiting out a press on the body (item 5); and the records: the guide's
   Raw clause and its Waiting on you parenthetical with their pins, the history module's git-free half, the ledger's
   `where:` line naming styles-fileview-err-sizes.test.ts, this note's word for a review role replaced by the round
   that measured, the keyboard-frames leg's header naming its two guards, place-memory case 6's sequence, and this
   note's sentences on each of these. The review's round 4 (2026-09-13) closed, each with a test red over a `git
   archive` of 7fbced030 where this sentence does not call it a pin: the ring at a keyboard-driven open whose opener
   is no element or is gone at the landing (`ringInOld`, `watchInputKind`, `ringWithNoHolder`) and the ring on the
   first key after a ringless hand-over (the body's keydown), item 1; a fold the record's state put back left as it
   says, the other-view open reading the record's `top` sign, a record's folds held past a Raw first paint, and a
   first paint under a boxless body keeping the record pending (item 3); the bar's raise waiting out a press on the
   body row, the aside included (item 5); and the records: the recent-place leg's third case pinning the re-seat's
   scroll and paint retires as behaviour (a behavioural pin of round 3's code: the retires are 7fbced030's, so the
   case is green over that archive and red over the two mutants round 4 measured, the `stands` guard made never to
   fail and renderBody's dropReseat call removed; its comment says so since round 5), the history module skipping and
   never erroring under `-W error` in a checkout without the shas (two cases, git stubbed to answer as for a sha the
   clone lacks, so they run in every checkout; the `-W error` case is the red one, the warns-then-skips case a pin of
   round 3's notice), this note's claim that the recent-place leg's stored-keys pin gained the fold field corrected
   (the pin keeps its eight fields; its message changed), and this note's sentences on each of these; the openers
   leg's Reload case is a behavioural pin of round 3's record, green over that archive, and says so (the review's
   round 5: round 4's record had counted the recent-place case among the red ones and left the history item's second
   case unsaid). The review's round 5 (2026-09-13) closed, each with a test red over a `git archive` of ad612d193
   where this sentence does not call it a guard: the open's line, offset and heading and its keyboard hand-over
   waiting for a body with a box (items 4 and 1); the leave under a boxless body writing the last measured place, a
   Raw leave carrying the folds a Raw first paint held, and the other-view fold rule reading the record's `atTop` and
   the body's height (item 3; the fold leg's forty-row comment case is a guard, shut before and after); the Recent
   rows read for the file by `placeKey` (item 3); the raise waiting for a parked landing's settle, the Reload on the
   words' line and the Comment float hiding at the bar's raise (item 5); and the records: the round 4 paragraph above
   on the two pins, the comments matrix sentence naming the round that read the cells, the guide module's heading-gate
   pin re-aimed to `spendHeading`, the ledger's `where:` line, and this note's sentences on each of these. The
   review's round 6 (2026-09-14), the cap under the owner's efficiency plan, closed, each with a test red over a `git
   archive` of 85fa51bf5: the other-view fold rule running over a fold the carried state put back shut when that fold
   is the Raw record's block, the boxless leave following the last measured place into the text a reload landed under
   the hide, and the show's report reading the offset the browser restored over a scroll the hide kept from being read
   (item 3); and the raise's release guard reading whether the body still shows the file the HEAD compared against
   (item 5); and the records: `placeKey`'s doc comments in file-view.ts, files.ts and files-recent.ts stating the
   rule's limit at one kernel, the tests-by-file counts, the ledger's `where:` line, and this note's sentences on each
   of these. The review's closing pass (2026-09-14), after the cap, closed the three edges round 6's own fixes had
   left, each with a test red over a `git archive` of 14a246665: the visible leave after a reload whose seat clamped
   following the held place into the text that landed as the boxless leave does (`liveRecord` reads `measuredPlace`
   under `held`, the one test `keptPlace` uses; place-memory case 10), the unread-scroll flag cleared by the
   measurement it stands in for, a read of the place or a clamped seat's hold, and no longer by the repaint alone
   (place-memory case 11), and the show's repaint seating the place when the browser's restore moved the body to below
   it, told by the restore's own scroll event with its frame read pending, the Raw view's short restore near the
   note's end (boxless leg 5); and the records: this note's sentences on each of these (items 3 and 4), the
   tests-by-file counts, the ledger's `where:` line, and the pins re-aimed in file-view-place, file-view,
   file-view-text-size and place-memory. After this pass the owner's termination rule applies: only a wrong mapping or
   a Rendered comments regression reopens the review. Recorded in the closing pass, not changed: the rule above reads
   the restore's scroll event at the show's repaint, where the harness puts it (the viewer's overlay hidden by a rule
   while the pane's document renders, so the hide's frame read runs and the show's width report follows); in a Files
   pane whose iframe the parent hides, rendering pauses with the iframe by the event loop's rules, so a scroll's frame
   read pending at the hide runs at the show, finds a box and reads the restored offset as the reader's, exact in
   Rendered and short in Raw near the note's end, with no width report and no flag for the repaint to act on
   (unmeasured here: the boxless legs model the pane's hide as the overlay's rule); it waits on the layout pass that
   clamps the restore, its cause inside Chromium unverified, since nothing the read measures tells a restore's scroll
   event from a reader's. Recorded in round 6, not changed there (the PR review's round 1 fixed the first two entries,
   item 3's key and item 1's pane toggle, as they say): an absolute or `~` path named by a session of this kernel and
   by a session attached from another kernel (a `host:`-prefixed sid, host-prefix.ts's `hostOf`; the viewer's read
   goes through preview.ts's `fileUrl` to `/remote/<host>/file`, the kernel's `_remote_file`, and that kernel's disk)
   was two files under one `placeKey`, so a reopen of either seated the other's later record, in the page's map since
   round 2 and through the rows' `latestPlace` after a reload since round 5, the span landing where a block of the
   other file's text starts at the same offset, else the clamped numeric scrollTop, and either file's leave overwrote
   the key for both (item 3; not on main 0bf0465b4, which keeps no place; the review's round 6, from a
   headless-Chromium probe over the real Files page with the remote route served as another text); it waited because
   the path key was the brief's decided default (question 7), and the PR review's round 1 ruled the fix, the host
   folded into the key of an absolute or `~` path for a remote session, read from the sid's host prefix as `fileUrl`
   reads it, built as item 3 says and pinned over the real Files page; a Comment float the reader Tabbed onto losing
   the keyboard when the
   panel hides it at the bar's raise, recorded above beside routing (a) and below with the Tab-focused highlight, the
   same drop; a Files pane toggled off and on after the landing dropping the body's keyboard to the pane document's
   body with nothing re-taking it at the show, item 1's edge, recorded below and fixed in the PR review's round 1 as
   item 1 says; the other-view bound judged against the
   reopen body's height, recorded in item 3; and a later one-line notice taking the changed-on-disk line, recorded in
   item 5. Recorded in round 5, not changed there: a heading target under a plain `hidden` wrapper, pre-existing and
   routed below, stood as round 4 recorded it until the PR review's round 1 gave the notice its words (item 4), and a
   Tab-focused in-body path link losing the keyboard at a poll's landing,
   pre-existing, is recorded below with the Tab-focused highlight, the same edge. Recorded in round 2, not changed:
   the Outline button's wrap of the actions row at 800 and 900 px, an accepted cost measured in item 2; and the
   Outline focusout closer's null case, whose comment now names its two moves (a window blur, the body taking the
   keyboard for the return; a move into another frame, whose own holder keeps it, read from the holder and never a
   flag), round 2's change to that closer being its comment alone, `closeOutlineKeeping` byte-identical at c88444f85
   and 27c56fbf7, so the keyboard-frames leg's Outline scene and its plain-holder scene are guards, green over the
   c88444f85 archive when run alone, where the relayed open, the Reload's landing, the re-arm and the Save's ack are
   red (the review's round 3: round 2's record had counted the null branch among the code changes with a
   fails-before). Round 2's two follow-ups of the remembered seat in item 3 (an open fold whose summary sits at or
   below the edge, the numeric fallback under late-loading pictures) were closed in round 3 (item 3). Recorded in
   round 1, not changed there: the Outline's first row current at the open (item 2, a design call for the owner, which
   the PR review's round 1 ruled the other way, the section under the reader's eye); round 1's other record, the
   relayed open taking the keyboard from the chat composer in the sibling iframe, was reversed and
   fixed in round 2 (item 1). Pre-existing edges outside the items, recorded and routed, not fixed (two entries below,
   the pane toggle and the hidden wrapper, say the PR review's round 1 fixed them; the rest it accepted as routed
   follow-ups): the URL viewer without the keyboard take and the Outline (items 1 and 2); the failure pane taking no
   keyboard (item 1); a
   `file://` URI written in a shown file's own text with a section on its tail
   (`file:///repo/notes-api/docs/report.md#results`), which the viewer's walk links with the section still in the
   path, so the click asks the kernel for `report.md#results` and gets its 404, where the same URI with `:12` on its
   tail links the file at line 12 and a bare `docs/report.md#results` on the same line links the file and leaves
   `#results` as prose (path-links.ts cuts a URI's swallowed `:12` under `lineSuffix`, which the viewer's walk passes,
   and its swallowed `#results` under `targetSuffix` alone, item 4's option for the todo surfaces; the same on main
   0bf0465b4; the review's round 2, from a headless-Chromium probe over both trees, and the comment at the cut says
   so; the follow-up is a call between cutting the swallowed section back to prose under `lineSuffix`, as the bare arm
   reads it, and the viewer's walk reading sections, a widening of open question 11's default); at the default text
   size the reset control between A- and A+ wears `.fileview-size-reset.fileview-size-default { visibility: hidden; }`
   in both sheets, so its 59 px slot is not hit-testable and a press that lands on it, or in the gap beside A+,
   reaches the actions row, which is not focusable, Chromium clears the focus to the document's body, no button click
   fires, and whatever held the keyboard loses it: the Comments panel's box, whose next words typed land nowhere
   (identical on main 0bf0465b4), or the viewer's body (item 1, so this face is new to the branch: PageDown scrolls
   nothing until the next click in the note), measured with real mouse presses over both trees; a `pointer-events:
   none` on the hidden slot changes nothing, and the fix, a `mousedown` default prevented on the actions row for a
   press on no button or a hit-testable no-op slot, changes the text-size control main ships (the review's round 2);
   the editor's exit repainting the text view at the top, so Edit then Cancel or Save and then a close records the top
   (item 3; identical on main 0bf0465b4; the routed fix seats `editPlace` at the exit's repaint; the review's round
   3); the keyboard-activated span opener keeping the focus, routed with the button-typed opener (item 1, the review's
   round 3); and the reader's place across a Rendered, Raw, Rendered swap in the round 1 comments matrix, where the
   top block after the swap differs from the one before it in the constructs@500 and tracked@800 cells, the same pair
   of blocks on the branch and on main 0bf0465b4 (re-read in round 2, which read the tracked@300 and tracked@500 cells
   as well: those keep their block, the scrollTop moving with the view since they start in Raw); a Tab-focused
   highlight loses the keyboard when a reload's landing removes it (the Comments panel's poll after a peer's write):
   renderBody's replaceChildren removes the mark, and an in-body path link the reader Tabbed onto goes the same way,
   the panel owning no mark for it (the review's round 5), the browser's fixup drops the focus to the document's body
   before the panel's onRendered reads its held mark, so its refocus never runs and PageDown scrolls nothing until a
   click, identical on main 0bf0465b4 (item 1: a reload's landing takes no keyboard by design; the routed fix is the
   panel's, reading the held mark before the swap, or the landing handing the keyboard to the body when it removed the
   holder, which covers both faces; the review's rounds 4 and 5); a Comment float the reader Tabbed onto (Tab past the
   aside's last control reaches it) loses the keyboard when the panel hides it: at the changed-on-disk bar's raise the
   body row's size report re-runs the float's subject test (round 5's fix, item 5) and the passage has moved, 61 px at
   a 900 px pane, so `float.hidden = true` drops the focus to the document's body and nothing hands it over (a drop of
   the panel's, uncaught under routing (a) above); before round 5 the float stood visible and focused 119 px above the
   passage until the panel's poll fetched the moved file and its landing hid the float at the paint, the same drop up
   to 2.5 s later, and that landing drops it so on main 0bf0465b4 too (the panel's `onRendered` hides the float at
   every paint there), so round 5 moved the drop's moment, not the drop; after it a PageDown still scrolls the body
   when the reader's last press was in it (Chromium starts a keyboard scroll from the last mouse-press node when
   nothing holds the keyboard, and the drag that offered the float is such a press: 0 to 69, then Space 69 to 372,
   where before round 5 the focused float swallowed both keys and the Space opened the composer) and scrolls nothing
   after a press outside it (a click on the bar's empty area, a keyboard selection and a Tab onto the float: 0 to 0 on
   both trees), so the branch is never worse for the keyboard than the tree before that fix (the review's round 6,
   real Tabs over both trees in headless Chromium; the routed fix is the panel's, the one the highlight's clause
   names: the hide handing the keyboard to the body when it removed the holder); a Files pane toggled off and on after
   the landing (the shell hides the pane with `display:none`, its rule `body:not(.po-files) #files-pane`; a phone
   swaps tabs) dropped the body's keyboard to the pane document's body by the browser's focus fixup, and the show's
   repaint re-took nothing since `keyboardOnLanding` is spent at the first landing, so PageDown scrolled nothing until
   a click, and an Outline popover open at the hide is closed by its focusout closer; an edge of item 1 (main
   0bf0465b4 never gave the body the keyboard), identical on ad612d193, measured twice in round 6 in headless Chromium
   through the shell's real rule; the routed fix, a re-take at the show's repaint through `takeKeyboard`'s gate when
   the body lost the keyboard to the document's body under the hide, waited as a design extension (the review's round
   6) until the PR review's round 1 ruled it into this slice, the edge being new to the branch, and it is built as
   item 1 says (`bodyHeld`, `retakeAfterHide`); with the Comments panel closed the card's Tab order ends at the body
   and the in-body path links,
   and the next Tab leaves the card for the browser chrome and then the document's first focusable, in the chat the
   composer behind the dimmed viewer, where typed letters land (identical on main 0bf0465b4, whose order ends at the
   links; round 3 returns a Tab from the Outline popover to its button alone; the routed follow-up is a focus
   containment for the card, a design call; the review's round 4); and a heading target under a plain `hidden` wrapper
   (a `<div hidden>` around the heading, or an `<h2 hidden>`) opened the file at its top with no notice,
   `scrollToFragment` finding the heading by its id, `revealFragmentTarget` lifting `until-found` alone,
   `scrollIntoView` on the boxless element moving nothing and the landing counting as done, the same on main 0bf0465b4
   through the old `frag` option (round 3 closed the Outline half, no row for such a heading; the routed fix was a
   notice naming a hidden section, since "No section named" would be false of it, its wording left open; the review's
   round 4), and the PR review's round 1 gave the words, built as item 4 says (`HIDDEN_SECTION`, `sectionHidden`).
   Tests, by file (every new node test on the shim's stand-ins with `hideEdges`; every browser leg
   over headless Chromium and the real bundles, 0 skipped, counted on every run): file-view-seam (39, eight new),
   file-view-focus-body-browser (3 legs, new), fileview-parity (4, nine heads; the changed-on-disk bar's Reload rule
   in round 5; the `.fileview-btn.on` pair in place of the Outline button's twin and a case holding the twin gone in
   the PR review's round 1), file-view-place (8, two re-pinned, one in round 4, two and a narrowed one in round 5, two
   in round 6,
   four re-aimed in the closing pass), file-view (53, four new and six re-pinned; pins re-aimed in rounds 4, 5 and 6
   and in the closing pass; one new and pins re-aimed in the PR review's round 1; the `land` and words pins re-aimed
   and the reason constants pinned in its round 2), file-view-links (28, re-pinned), md-url-view (29, re-pinned),
   pdf-new-tab (12, re-pinned), file-view-notebar-browser (9 legs, one new and one re-aimed in the build, three in the
   review's round 1, one of them restructured in round 2 into six holder cells and given a seventh in round 3, one new
   in round 3, and two in round 5, the third reading the bar's role per cell in the PR review's round 1),
   file-view-place-memory (13, new; case 6 re-aimed in the review's round 3, two pins in round 4, one in round 5, one
   re-aimed and one added in round 6, two cases and one re-aimed pin in the closing pass, two new cases and one
   extended in the PR review's round 1), file-view-place-svg-source (1, re-pinned), file-view-reload (22, ten new in
   the build, two in the review's round 3, one extended in rounds 4 and 5, one new in round 6, one new and one
   extended in the PR review's round 1, two new in its round 2), file-view-outline (15, new; the closers case counting
   over the module's listener since round 4; four new, three re-pinned and one rewritten in the PR review's round 1;
   one new and one re-pinned in its round 2), file-view-outline-browser (5 legs, new, one extended in round 2, a
   fourth and two re-aimed in the PR review's round 1, a fifth in its round 2), files (16, two new; the fold field in
   round 3; one in round 5 over `latestPlace`; the executed case extended in the PR review's round 1),
   files-recent-place-browser (3 legs, new; the third extended in round 4), file-view-place-memory-fold-browser (13
   legs, new; four in the review's round 4, two in round 5, one in round 6), file-view-keyboard-frames-browser (2
   legs, new in the review's round 2; comments in round 3), feed-viewer-focus-browser (2 legs, new in the PR review's
   round 1, a record), ui/test-dom-shim.test.ts (13, the shim's NON_DOM_EDGES list gains that leg's file, whose feed
   card carries a goal tree with an empty children array, a card model and no DOM edge, and NON_DOM_EDGES_MAX rises
   from 2 to 3, the PR review's round 1; named here since its round 2, the round 1 records having missed it),
   file-view-focus-ring-browser (3 legs, new in the review's round 3; the third in round 4),
   file-view-focus-ring-openers-browser (2 legs, new in the review's round 4), file-view-boxless-browser (7 legs, new
   in the review's round 5, two in round 6, one in the closing pass, two in the PR review's round 1),
   files-recent-place-shared-browser (2 legs, new in the review's round 5, a second in the PR review's round 1),
   path-links (15, five new), render-open-path-target (5, new), user-todo-links (12, cases extended and re-pinned),
   waiting-detail-link (5, one new), todo-link-target-browser (2 legs, new), waiting-file-chip (12, re-aimed),
   user-todo-title-links (12, re-pinned), url-links (15, re-pinned), file-uri-link (4, re-pinned), chat-space-paths
   (5, re-pinned), user-img-dedup (4, re-pinned), render-todo-file-chip (14, re-pinned), waiting-link-focus (4,
   re-pinned), waiting-pane-browser (6 legs, re-pinned), chat-relpath-link (6, re-pinned), menu-theme-tokens (7, the
   surfaces list), file-comments (35, one re-pinned), file-view-text-size (33, one count pin re-aimed in the review's
   round 5 to the width frame's reshaped repaint, in round 6 to its restored branch, and in the closing pass to its
   moved-restore test), styles-fileview-err-sizes (7, one pin admitting a line in the review's round 2), the fixture
   file-view-outline-fixture.ts (new) and real-viewer-leg.ts (the HEAD-aware stub, `__heads`, `chatKeysScript`; the
   404's reason from `__reason` since the PR review's round 2); tests/test_files_pane.py (24, one new),
   tests/test_kernel_preview.py (29, two new and two extended in the PR review's round 2: the 404 reason `missing`,
   `unresolved` and `relative`; two new in its round 3: `unreadable` for a file under a directory made mode 0 for the
   test's duration, and `missing` pinned for ENOENT, ENOTDIR, a directory at the name and a NUL byte in the path),
   tests/test_kernel_remote_file_relay.py (20, one new and three extended in the PR review's round 2: `detached`,
   `unviewable` and the mirror of a remote's known word; one new and one extended in its round 3: a known word on a
   remote 200, 413 or 500 not mirrored, GET and HEAD, and `unreadable` among the mirrored words),
   tests/test_guide_files_place_and_outline.py (14, new; two pins re-aimed in round 4, the heading gate's and the
   Recent lookup's in round 5, the disk bar's in the PR review's round 1 and again in its round 2, to the reason
   header's read), tests/test_reference_todo_file.py (20, two re-pinned),
   tests/test_markdown_viewer_plan_note_history.py (10, five in the review's round 2: the head's sentence on the three
   commit messages, checked against the history it names; three in round 3: the same claims held to the facts the
   module states without git, so CI's depth-1 checkout pins the note and the history half's skip is named in the run's
   warnings summary; two in round 4: the skip standing under every warning filter, `-W error` included, git stubbed),
   tests/test_markdown_viewer_plan_note_counts.py (5, unchanged; it accepts this note). Every case that changes
   behaviour fails over a `git archive` of 4a3e18664 (the head the branch was cut from, the base 0bf0465b4's bytes in
   every file a test reads), of the fork's main while the build ran, 929ae86e1 (Slice 8's hunks absent there, in the
   six files the head of this note names), or of a head of the pre-rebase lineage (the mapping at the head of this
   note), with the new exports stubbed where a test imports one, and says how and over which tree in its commit (a
   review round's case over a `git archive` of the tree that round reviewed, d91f0c19d for round 1, c88444f85 for
   round 2, 27c56fbf7 for round 3, 7fbced030 for round 4, ad612d193 for round 5, 85fa51bf5 for round 6, 14a246665 for
   the closing pass, 3e433ceee for the PR review's round 1 and e6aeb1138 for its round 2); a pin over a shape this
   slice moved is titled a re-pin and is red by construction over those trees; the guards say they are guards. The
   guarantees the families re-verify: highlights are measured `<mark class="fc-hl">` elements over the range's text
   nodes with their data-act, id, tabIndex, role and title, the margin layout reading their boxes, and the panel's
   press-time strip takes the tabindex off marks alone, never off the body, whose own `tabindex` stands through a
   press; the panel's boxes, the editor and a mark keep the keyboard through every paint this slice adds a focus to;
   the poll asks one reload per mtime and the save fence compares mtime strings, and the probe reads the same header
   with the same two functions and never writes `mtimeNs`; the pairing, the change marks and the selection map read
   the one block table, which item 3's span check and item 4's offset landing READ and do not change; the Raw view and
   the anchor map are untouched; and the composer's quote stays the exact source slice.

**Manager review round 1** (2026-09-14). The manager's review of fork PR 753 at 3e433ceee over main 0bf0465b4, the
first review of the PR as distinct from the build's own rounds above; the code's comments and the tests call it "the
PR review's round 1". Nine findings confirmed (two medium, seven low) and one left to be settled, eleven fix items and
a ruling on each of the body's open decisions; the fixes were applied on the branch after the round, every code change
with a test red over a `git archive` of 3e433ceee unless this paragraph calls it a guard or a record, and the standing
rule held: nothing here touches file-comments.ts, and the comments suite and the viewer's neighbouring pins (251
cases) ran green beside the round's tests. What changed, why, and the test that holds it: (1) the Outline popover
under the card's press hold, `pressHold(box)` in place of `pressHold(body)`, so a landing during a press on a row
parks until the release and the pick lands, where the paint had removed the pressed row before the mouseup (item 2;
outline case 11, outline-browser leg 4). (2) The popover's focusout closer's three branches executed, one case each, a
guard checked under three mutations of the closer (item 2; outline case 10). (3) The feed document's focus-return
policy, `feedWantsKeys`, whose zero timer after a feed click was said to hand the page's focus to the chat frame right
after the viewer's body took the keyboard, and to restore a composer so the landing yields: measured in the real feed
bundle and refuted, no code change; the hand-back is inert in the dashboard because `returnFocusToChat` looks the chat
frame up by an id the served shell does not carry, and Chromium clears a frame's focused element when the focus moves
into another frame, so the restored composer does not hold either (item 1; feed-viewer-focus-browser, two legs, a
record). The stale id is a pre-existing condition outside the slice, routed below. (4) path-links' `targetSuffix` walk
cut a URI's swallowed line tail before its section tail, both anchored at the token's end, so
`file:///repo/notes-api/docs/a.md:12#results` kept `:12` in the path and carried the section as `data-frag`; the
section is now cut first and the line rides as `data-line` with `#results` left to the prose, as after the bare
`docs/a.md:12#results` (item 4; path-links case 12, 0/1 over the archive; the `lineSuffix` follow-up recorded above is
unchanged). (5) The media landing through the text landing's box guard, `landMedia` from the blob landing and from the
show's repaint, a line or an offset target on a picture or a PDF named in the notice bar where it was dropped in
silence, and the one-shot keyboard take no longer spent over a boxless body (item 4; place-memory case 8, boxless leg
6). (6) A HEAD answering 404 raises `Deleted on disk.`, the words read off the verdict and kept on the bar's record,
Reload painting the 404 pane with the button re-armed under the one-bar rule (item 5; reload case 13; the Python guide
module's disk-bar pin re-aimed). (7) The URL viewer's replace path executed in the place-memory suite beside its
source pin, a guard, red with `runLeave` removed from `openUrlView` (item 3; place-memory case 9). (8) The relay's
field and upstream's twin, recorded here and in the ledger entry: upstream's viewFile relay carries `frag`, a string,
the section a `path#slug` link names (upstream's T351), on the same message and the same forwarder line the fork's
`at` object rides: render.ts's `openPath(path, sid, ev, frag)` posts `frag: frag || null` where the fork's
`openPath(path, sid, ev, at)` posts `at`; the shell's Files pane forwarder copies `frag:m.frag||null` where the fork's
copies `at:m.at||null`; files.ts's `openHere(path, sid, identity, frag)` opens `{ frag }` where the fork's reads
`readAt(m.at)` and opens `{ todoId, at, place }`; `openFileView`'s options are `{ line?, frag? }` there and `{
todoId?, at?, place? }` here, and `initFileView`'s relay type reads `frag?: unknown` there and `at?: unknown` here.
The mapping: a `frag` string is `at: { heading: frag }` and back, a null `frag` a null `at`; the fork's `{ line }` and
`{ offset }` arms have no upstream field (upstream's `line` option is in-process, fed by no relay), and upstream has
no feed-branch forwarder, the fork's being fork-only since 2026-08-20. The rule for the offer: the port replaces
`frag` with `at` at every hop named, a `frag` string becoming a heading target. The rule for an inbound fold: an
upstream change to a `frag` hop lands on the fork's `at` hop at the same place, read through that mapping, and a new
upstream reader of `frag` becomes a `readAt(m.at)` reader whose heading arm carries the string. (9) Escape on the open
popover returns the keyboard to the Outline button, the menu-button pattern (item 2; outline case 4, outline-browser
legs 1 and 2). (10) The Outline button's open state is the bar's selected dress, `.fileview-btn.on`, toggled beside
aria-expanded and put on before the popover's box is read; the sheets' `[aria-expanded="true"]` twin dropped and the
`.on` heads added to the parity list (item 2; outline case 2, cases 7 and 8 re-aimed, fileview-parity's new case).
(11) `noteBar`'s div carries `role="status"` (item 5; reload case 6, notebar leg 3). Rulings on the open decisions,
fixed: the Outline's current row at the open is the section under the reader's eye (item 2; outline case 9,
outline-browser leg 1); `placeKey` folds the host into a remote session's absolute or `~` key, correctness over
sharing (item 3; place-memory case 7, the files suite's executed case, shared-browser leg 2 over the real Files page);
the Files pane toggled off and on re-takes the keyboard at the show's repaint, the edge being new to the branch (item
1; boxless leg 7); a heading target under a plain `hidden` wrapper shows `That section is hidden in the rendered view;
opened at the top.` (item 4; outline case 12); a 404 is a deletion, fix 6 above; and the Slice 8 note's routing clause
reads "a follow-up" alone. Accepted as recorded, so their entries above stand: the focusout closer closing on a null
relatedTarget (pinned by fix 2); the URL viewer without the keyboard take and the Outline, and the fetch-failure pane
taking no keyboard, as the brief scoped them; the remembered seat not holding a clamped write; the depth across a
width change landing near, and the other-view fold rule judged against the reopen body; `readAt` refusing a fractional
line; the conflict bar's Reload re-open passing `at`; the other routed edges (the text-size reset slot clearing the
keyboard, focus containment for the card, the editor's exit recording the top, the file URI section inside a shown
file's text, a Tab-focused highlight losing the keyboard at a poll's landing), each recorded above as a routed
follow-up; and the eleven commit messages citing pre-rebase shas, history, the mapping at the head of this note
sufficing. The media notice's words (`No line 12 in this file: it is a picture.`, the kind naming why there is nothing
to open at) are the build's, offered for a ruling. Records this round: this paragraph and the sentences above that
each fix touched, the tests-by-file counts, the ledger entry's `where:` line naming every file the round changes and
the mapping in (8), and the Slice 8 clause; docs/guide.md and CONTEXT.md are unchanged, the reasons in item 6. Routed
out of the slice, pre-existing: ui/webview/feed.ts's `returnFocusToChat` looks the chat frame up as `chat-frame`, an
id the served landing page does not carry (its frame is `f-chat`), so the feed's focus-return policy has been dead
code in the dashboard since the shell's rename, and its comment's claim that the hand-back restores the chat
document's last-focused element does not hold in Chromium; correcting the id alone breaks the viewer's and the
browser's keyboard (the four post-timer reads red in a scratch run), so a fix is the id and a `boardCovered()`
exception in `feedWantsKeys` together, which feed-viewer-focus-browser already holds (red with the id alone, green
with both); a call for the owner, not this slice. Process: review round 2 followed over the fix head, e6aeb1138, the
paragraph below; the two kernel relay lines still need the live kernel's restart at the deployment.

**Manager review round 2** (2026-09-14). The manager's review of fork PR 753 at e6aeb1138, the round 1 fixes, over
main 0bf0465b4, reading the change since 3e433ceee; the code's comments and the tests call it "the PR review's round
2". Seven findings confirmed, every one low, and one refuted; every round 1 fix held (the closer cases, the tail
order, the media notices, the URL viewer case, the frag mapping, Escape, the shared dress, the live region and the
five ruled decisions). Under the review's rules a round whose findings are all low closes the review once its items
are applied, so the five items below were applied on the branch, each code change with a test red over a `git archive`
of e6aeb1138; the kernel code this round added, new to the branch, was then read in a round 3, the paragraph below,
which closed the review, and the manager's own full test run, CI, the landing on the standing word and the deployment
note come next. The standing rule held again: nothing here touches file-comments.ts, the kernel change ran green
beside the comments note module (tests/test_kernel_file_comments_note.py with tests/test_perf_stats.py, 75 cases) and
the viewer's beside the notebar, boxless and seam suites (9 legs, 7 legs and 39 cases). What changed, why, and the
test that holds it: (1) A landing the card's hold parked under a press on the
Outline BUTTON ran after the release's click had opened the popover, on the hold's zero timer, and its paint closed
it, so the click appeared to do nothing (a face of round 1's fix 1, which moved the hold from the body to the card so
that a press on a row would park a landing). `fetchFile`'s `land` now reads the hold once before the defer and hands
the run a `parked` flag, and the text landing, when it was parked and a popover is open at its run, opens the popover
again after its paint, over the landed body, so the rows, the current row and the keyboard are read afresh; a landing
that ran at once still closes it, and one parked under a press on a row, or on the button with the popover up, finds
it already closed by the pick or the toggle and opens nothing. Of the two shapes the manager allowed, the parked
landing run ahead of the click's own handler or the popover kept across the landing's paint, the second was built,
scoped to landings the hold parked, the first needing a flush inside the shared press hold (item 2; outline case 15
and outline-browser leg 5, both red over the archive at the popover standing after the landing's paint; outline case
7's and file-view case 50's pins re-aimed to the re-open lines and the `land` shape). (2) Every HEAD 404 had been read
as a deletion, and the kernel's HEAD /file answers 404 for causes a shown file reaches after a successful GET with the
file still on disk, read from the handler: a relative path re-aimed by a session move (`SdkBackend._finish_move`
rewrites the names registry's cwd that `_resolve_open_path` joins the path to), a relative path with no cwd to join,
and, through the relay, a host detached since the GET. The kernel's /file 404, GET and HEAD, now names its cause in
one word, the `X-Romp-Reason` header: `missing` for an absolute or `~`-rooted path whose stat answers ENOENT or
ENOTDIR, the path or a parent gone, or finds no regular file at the name, the one value that means the file is gone
(narrowed so in the review's round 3, which found every failed stat reading `missing`); `relative` for a relative path
joined to the session's current cwd and found nothing there, which a move and a deletion produce alike, so the kernel
certifies neither; `unresolved` for a relative path with no cwd to join; since the review's round 3 `unreadable` for
an absolute or `~`-rooted path whose stat fails for any other reason (EACCES on a parent directory, a symlink loop, an
I/O error), the file possibly still there, so the kernel certifies nothing; the relay's own `detached` for a host no
longer attached and `unviewable` for an extension it refuses before dialing; and a remote kernel's word mirrored when
it is one of the local route's words (three then, four since round 3), dropped otherwise, as `X-Romp-Mtime-Ns` is
mirrored (`_file_404_reason`, `_FILE_404_REASONS` and `_FILE_404_REASON_HDR` in kernel/kernel.py; GET bodies
unchanged; the download half's 404 and do_HEAD's route miss are not on the probe's URL and carry none). The viewer
reads the header off the HEAD's answer and says `Deleted on disk.` for `missing` alone and
the change's words for any other cause or none, a kernel from before the header included, Reload then painting the
kernel's own pane for what the GET answers (`REASON_HEADER` and `REASON_MISSING`, exported for the pins);
real-viewer-leg.ts's page stub sends the header from `window.__reason`, `missing` by default (item 5;
test_kernel_preview four cases, two new and two extended, and test_kernel_remote_file_relay four cases, one new and
three extended, each red over the archive on the header's absence, `None` where the word was expected; reload case 21,
red over the archive with the deletion's words where the change's were expected: `relative`, `detached` through the
relay URL for a `TESTHOST`-prefixed sid and no header raise `Changed on disk.` and `missing` raises `Deleted on
disk.`; case 13 now says its 404 carries `missing`; tests/test_guide_files_place_and_outline.py's disk-bar pin
re-aimed to the new words line and the two constants, red over the archive). Two limits, recorded: `relative` is
deliberately not `missing` even when a relative path's file really was deleted, since the kernel cannot tell that from
a move, so that case shows the change's words, the price of never calling a moved session's file deleted; and no
`Access-Control-Expose-Headers` names the header, since the route exposes none of its custom headers cross-origin
today, `X-Romp-Mtime-Ns` included, the dashboard and the relay URL being same-origin, a pre-existing condition and not
this item's. (3) The words kept on the disk bar's record for the editor's exit re-raise had been pinned by source text
alone; the executed case: with the `Deleted on disk.` bar up, Edit takes the bar, Cancel brings it back reading
exactly those words with Reload armed, role status, no HEAD sent and the keyboard on the body, and Reload then paints
the 404 pane (item 5; reload case 22, green over the archive and at the head and red with the re-raise mutated to the
change's words; no code change). (4) The ledger entry's `where:` line had omitted ui/test-dom-shim.test.ts, which
round 1's commit changed (a NON_DOM_EDGES entry for feed-viewer-focus-browser.test.ts, whose feed card carries a goal
tree with an empty children array, no DOM edge, and the list's cap raised from 2 to 3), and cited reload cases by
numbers the file does not have; the line now names the file, numbers the cases by each file's own ordinal and names
every file this round changes, and the entry's body says the shim and its ratchet are fork-only until the shim
migration entry ports (item 6). (5) The round 1 paragraph above had cited reload cases 33 and 40 and place-memory
cases 21 and 22, numbers from a continuous count over three suites run together where each file numbers its own cases:
the role assertion is reload case 6 and the 404 case 13, the key case place-memory 7 and the media case 8, corrected
there and in items 3 and 5. The re-check of every other ordinal in this note against the files found two that round
1's insertions had moved and nothing else: its two place-memory cases went in ahead of the closing pass's, so the
clamped reload's visible leave is case 10 and the unread-scroll flag case 11, and its 404 case went in ahead of round
6's, so the parked landing newer than the HEAD's answer is reload case 20; the earlier paragraphs say so (item 6;
tests/test_markdown_viewer_plan_note_counts.py and tests/test_markdown_viewer_plan_note_history.py accept the note).
Refuted, no change: that the card's hold, parking a fetch under a press on the Edit button, lets the click's
`enterEdit` run before the parked landing and open the editor on stale text. `enterEdit` is reached through
`ensureEditingAllowed`, which awaits a GET /version first, a network round trip, and the parked run's zero timer fires
before that answer; in Chromium, and in the harness once its /version stub answers on a macrotask as a fetch does, the
parked landing paints before the editor opens, the harness's microtask-fast stub being the one place it reproduced.
Records this round: this paragraph and the sentences above that each fix touched (the head's summary, items 2, 4, 5
and 6, the tests-by-file counts, with file-view-reload at 22, file-view-outline at 15 and file-view-outline-browser at
5 legs, and the two kernel modules and the shim test named), the ledger entry's `where:` line and its body, and the
round 1 paragraph's ordinals; docs/guide.md is unchanged, its changed-on-disk sentence quoting no words, and
CONTEXT.md is unchanged, the round coining no term. Deployment: the /file route's 404 reason and the two viewFile
relay lines are served by kernel/kernel.py, so they reach the dashboard only after the live kernel's restart, and
until then every HEAD 404 shows the `Changed on disk.` fallback with Reload, a real deletion included; a remote host
whose kernel predates the header answers its 404 without it, so a file deleted there reads as the fallback until that
host's kernel restarts on the new code too. The consolidation's full run found two source pins the round's shapes
had moved, re-aimed with no count change: file-view-links.test.ts's landing pin, which now allows the
`reopenOutline` lines between the text's assignment and the target, and user-todo-links.test.ts's kernel pin, which
now reads the `given` name `_file_preview` keeps the request's path under for the 404's reason. With this round the
review was to close; the manager read the kernel code it added in a round 3, the paragraph below, and the review
closed there.

**Manager review round 3** (2026-09-14). The manager's review of fork PR 753 at 4a1c02fe8, the round 2 fixes, over
main 0bf0465b4, reading the change since e6aeb1138, whose kernel code was new to the branch; the code's comments and
the tests call it "the PR review's round 3". Three findings confirmed, every one low, none refuted; the header's
exposure, the route's gates, the HEAD path, the relay's mirror and the viewer's fallback all held. An all-low round
closes the review once its items are applied, so the three items below were applied on the branch, each code change
with a test red over a `git archive` of 4a1c02fe8, and no round follows them: the manager's own full test run, CI, the
landing on the standing word and the deployment note come next. The standing rule held: nothing here touches
file-comments.ts or the viewer's code (two comments in file-view.ts name the new word, no line of code); the change is
one function and one tuple in kernel/kernel.py and two of its test modules. What changed, why, and the test that holds
it: (1) `_file_404_reason` had answered `missing`, the one word the viewer shows as `Deleted on disk.`, for every
absolute path with no regular file at it, and the route's `isfile()` swallows every OSError alike, so a file under a
directory the kernel may not search (EACCES on a parent) read as deleted while it existed. The function now stats the
absolute path itself, after the `unresolved` and `relative` checks, and answers `missing` only when the stat says
ENOENT or ENOTDIR (the path or a parent gone), finds no regular file at the name (a directory stands there now), or
the path carries a NUL byte, which no file can (a ValueError from `os.stat`, outside the ruling's split into ENOENT,
ENOTDIR and any other OSError; the route must catch it, since the new stat would otherwise 500 a request `isfile()`
had swallowed, and `missing` was chosen, a choice put to the manager: one word in the except tuple and one row of the
pin change it to `unreadable`); any other OSError (EACCES on a parent directory, a symlink loop, an I/O error) answers
a fourth word, `unreadable`, the ruling having allowed the word or no header: the file may well exist, the kernel
could not look, so it certifies nothing, and the viewer shows the change's words with Reload, its reading rule
unchanged (`REASON_MISSING` alone means deleted; every other word falls back to `CHANGED_ON_DISK`).
`_FILE_404_REASONS` holds the four words, so the relay mirrors a remote kernel's `unreadable` as it mirrors the other
three; the comment block over the constants and the function's docstring name the word and why (item 5;
test_kernel_preview's EACCES case, a file under a directory made mode 0 for the test's duration with the mode restored
in the cleanup, skipped with its reason as root, where EACCES cannot be produced: HEAD 200 first, then HEAD and GET
404 `unreadable` with the GET body as it was, the file shown on disk once the mode is back and served 200 again, red
over the archive at `missing` on the HEAD; a second case pins `missing` for ENOENT, ENOTDIR, a directory at the name
and a NUL byte, GET and HEAD, green over the archive and red under a build answering `unreadable` for ENOENT; the
relay module's mirrored-words case extended with `unreadable`, red over the archive with the word dropped as unknown;
over the archive the two modules read 2 failed, 47 passed, at the head 49 passed). One limit, recorded: GET bodies are
unchanged, so Reload after an `unreadable` HEAD paints the kernel's 404 pane, not found over a file the kernel could
not read; a body naming the cause is a follow-up if wanted. (2) The relay's mirror is guarded on the remote's status
as well as its word, `status == 404 and r_why in _FILE_404_REASONS`, and no case held the guard: dropping it changed
no verdict. A pin, no code change: the fake remote's 200 (plot.png) and 413 (big.pdf) arms and a new 500 arm
(boom.png) send `X-Romp-Reason` when a case sets one; the new case sets `missing`, requests each by GET and HEAD,
asserts the relayed status is the remote's and the header absent, then that the same word on the remote's 404 still
rides (item 5; the case is green over the archive and red with the guard dropped from the relay line, every older case
green under that build, which is what the finding said). (3) The ledger entry's `where:` line had called the round 1
path-links case a fifteenth, the file's count, where the same line cites the reload suite's cases by ordinal, so the
phrase read as an ordinal and pointed at the linkTarget case; by the file's ordinal it is case 12, corrected through
scripts/upstream-ledger.py set, and the re-check of every other ordinal in the line against the files found the rest
right: reload cases 6, 13, 20, 21 and 22, outline cases 7 and 15, outline-browser legs 4 and 5, notebar-browser leg 3,
files-recent-place-browser leg 3, focus-ring-browser leg 3 and files-recent-place-shared-browser leg 2 (item 6;
records only). Records this round: this paragraph, the round 2 paragraph's list of reason words, its mirror sentence
and its closing sentence, item 5's count of the reason cases, the ledger-entry sentence and the tests-by-file counts
above (tests/test_kernel_preview.py at 29, tests/test_kernel_remote_file_relay.py at 20), and the ledger entry's
`where:` line (the kernel clause, the file-view.ts clause, the two test modules' clauses, the plan clause and the
ordinal) and its body; file-view.ts's two comments on the header's values name the fourth word; docs/guide.md and
CONTEXT.md are unchanged, the round coining no term. Deployment: `_file_404_reason` and `_FILE_404_REASONS` are
served-route code in kernel/kernel.py, so like round 2's header they reach the dashboard only after the live kernel's
restart; until then a file under an unsearchable directory still reads `missing` and the bar says `Deleted on disk.`
over it. With this round the review closed; the owner's termination rule stands, only a wrong mapping or a Rendered
comments regression reopening it.

### Slice 7: every failure says what happened

The render catch shows Raw rows under a `.fileview-err` line; a failed figure shows an inline error
naming its src; every failure path fires the paint hooks and the seam exposes `error()`; the host
strips the BOM and the kernel re-prepends it on save; a Latin-1 file's note bar says why Edit is off;
an empty file says so; Raw splits rows on CR, CRLF and LF. Acceptance: every case shows text, never
a blank or bare glyph; `mode()` answers raw after a thrown render; a failed reload ends the panel's
wait at once; change marks paint on a BOM file whose saved bytes still begin EF BB BF; a three-line
CR-only file gives three Raw rows. Tests: file-view, seam, host;
`tests/test_kernel_file_comments_save.py`.

**The Slice 7 build** (2026-09-14). Branch `mdviewer-s7`, cut from e6aeb1138, the head of `mdviewer-s6` (Slice 6, fork
PR 753, in the manager's queue when the build began), every commit on it self-contained so that the branch could
rebase onto the fork's main once that PR landed, the PR opening against main after the rebase (the brief's open
question 1 at its default, decided by the session that directed the build as the worktree's base; Slice 6 and Slice 8
were cut the same way). After the build's consolidation commit it was rebased on 2026-09-14 onto main 462ad3ccf, the
merge of PR 753, the branch's base since. The rebase re-minted every commit, so a sha a commit message names for a
fails-before tree is a tree no clone of the fork reaches, unless it is e6aeb1138 itself, which PR 753 carried onto
main (the six such shas: 7c8a1905c, 123dcc8a9, fc6213e9a, f7902d170, 1512a28c4 and 07cbca7bc). The mapping, which `git
range-diff e6aeb1138..9d0c719a0 462ad3ccf..103a13f32` reads as the same patch commit for commit (the branch through
its consolidation commit; the same range ending at a later head lists the review's commits after it as unpaired), with
the build's label for each (the labels are the build's units, one builder each owning its files, under one session
that directed them): 0ce202051 (A1) is 023da39f1 on the branch, 934c7e6b6 (B) is db4bffd58, e5b44a89d (C1c) is
5e6728847, 1af2be2bd (D1) is 44462600a, 123dcc8a9 (C0c) is 6e9f977e9, 6299665d0 (C4c) is ba3cd2d40, 954e55c9a (A2) is
eac826b13, cb9aca26d (D2) is a58644912, a874ba578 (D3) is 79133ebdc, f7902d170 (C3c) is fcf8208ff, d1b0f6d62 (A3) is
69559aeb8, 284d63f2c (C2c) is a5b8a51a0, fc6213e9a (A4) is 7d2758183, 07cbca7bc (A5) is 20b573ff4, 1512a28c4 (A6) is
97b6ec958, 441a70c4b (A7) is 3028370df, 5902b1265 (E1, the guide) is 4167fb59b, ad7667f20 (E2, this note) is
c689a845d, 7c8a1905c (E3, the ledger entry) is 32cad5f72 and the consolidation's 9d0c719a0 is 103a13f32. Eighteen of
the twenty replayed as the same patch; the range-diff shows what changed in the other two. A3's two hunk headers in
file-view-reload.test.ts quote the title of the deleted-on-disk scene, which main's round 2 had renamed; the patch's
lines are the same. A5 conflicted in two files main had also changed, file-view-links.test.ts (the landing-order pin)
and real-viewer-leg.ts (the page stub's globals line), and two more pins merged clean but each allowed its own side's
line alone: A5's landing-order pin in file-view.test.ts and main's re-open pin in file-view-outline.test.ts. The
replayed A5 carries both sides in each of the four: the two landing-order pins and the re-open pin allow main's
`reopenOutline` line before the paint and the Latin-1 raise after it, and the globals line carries main's `__reason`
and A5's `__utf8`. Main's two commits between e6aeb1138 and 462ad3ccf, Slice 6's manager review rounds 2 and 3
(4a1c02fe8 and c5b89724d), change fourteen files, nine of them files this slice changes too: kernel.py, this plan,
tests/test_kernel_preview.py, file-view.ts, real-viewer-leg.ts, file-view-links.test.ts, file-view-outline.test.ts,
file-view-reload.test.ts and file-view.test.ts. So a fails-before run over a `git archive` of e6aeb1138 read those
nine at the cut point, not at the base. Every count in this note is the count on the branch, main's two rounds'
additions and this slice's review's own included: file-view-reload.test.ts 23 where the cut point had 20 (two cases
from main's round 2, and the failed Reload's 413 scene from this slice's review's round 2) and
file-view-outline.test.ts 15 where it had 14 (main's round 2's case), tests/test_kernel_preview.py 31 where it had 25
(two cases from each of main's rounds); the review's round 1 corrected these three, written at the cut point's numbers
plus the slice's own (20, 14 and 27), and its round 3 the first of them, left at 22 when round 2 added its scene. No
commit of the build claims a file byte-identical between two trees, so nothing here is for the history module to check
(tests/test_markdown_viewer_plan_note_history.py reads the Slice 6 note alone). The units: A the viewer (file-view.ts,
md-sanitize.ts for its sanitizer seam, real-viewer-leg.ts and the viewer tests), B the sheets (the two sheets' viewer
regions and fileview-parity), C the panel and the map (file-comments.ts, anchor-map.ts, reader-place.ts and their
tests, and the stub sweep), D the host and the kernel (file-comments-host.mjs, kernel.py's `_save_file` and edit log,
and their tests) and E the records (the guide, this note, the ledger entry). Every shape one unit coded against in
another's file went through a contracts file in the notes directory outside the repo, one dated line each, written
before the code that met it: C1 the seam's `error()`, C2 the figure label, C3 the panel's row, C4 the BOM rule, C5 the
five exported strings, C6 the row split, C7 the text paint's try. This note and the ledger entry are E2 and E3, mapped
above; the consolidation pass followed as one commit after them (it re-aimed the three source pins in unit C's files
that read lines A7 changed, item 7; added the failures leg's panel scene and the landing's clearing of the panel's row
that scene found, item 3; left the failed figure's label out of the Rendered pairing's top-level nodes, the defect its
full npm test's browser legs found, item 2, and re-aimed the one sanitizer pin the audit missed, item 1; and updated
this note), then the rebase onto main, and the review (its rounds recorded below), the sweep and the PR. The principle
every item serves, in one sentence: a failure shows text naming what happened where the person is looking, never a
blank, a bare glyph or a console-only error; a source that cannot answer says so rather than degrading to a guess; and
a mechanism fires on the exact event (an img's `error` event, a fetch chain's catch, the landing that applies bytes,
the header a response carries), never a timer, a debounce, a grace period or an age threshold. What each item does,
why, and the test that holds it:
1. *Item 1, the render catch.* `mdBlock` keeps no try, no catch and no `rendered` flag: a throw from marked, from the
   sanitizer or from any DOM pass in it propagates, and both link passes run on every successful render. Each viewer's
   `renderBody` (the local viewer's text paint inside `perfTimed`, the URL viewer's) wraps the block's build AND the
   swap in one try; on a throw it paints the exported `RENDER_FELL` line (`div.fileview-err`, the body's first child,
   the sentence with the message in parentheses and then the period; no hint row, since the title bar names the path,
   and no Download, since the text is showing) and `codeBlock(text, path, true)` under it, the file's text as Raw
   rows, and records the message in a per-open `renderFell` (the build recorded an Error's message, else
   `String(err)`, before the fallback swap; since the review's round 2 the record follows the swap and reads
   `fellMessage(err)`, below); a throw from that fallback propagates (a second failure is a bug, not a file; at a
   landing it reaches the fetch chain's catch). The rest of the pass runs as before, so the hooks fire once, the
   reader's place reads the rows, and a leave from that body writes a Raw record (the rows are a text view). `mode()`
   answers "raw" while `renderFell` is set, so `renderedImages()` answers `[]`, the Outline hides, the Comments panel
   pairs over `code.hljs`, and `scrollToOffset` and `scrollToLine` find the rows; the Rendered button stays pressed
   (the person's saved choice; the line says why rows show), the Raw click clears the line and the record, the
   Rendered click tries again, and a reload's landing runs the try again. `error()` (item 3) stays null over the rows:
   they are the content, and `mode()` is that paint's word. Before the slice the catch inside `mdBlock` wrote the
   file's source into the Rendered box as one text node with `rendered = false`, which skipped the two link passes
   alone; the box had no white-space rule, so the source read as one unannounced paragraph with `mode()` still
   answering "rendered" from `fmt.md`, and a throw after that try or from the swap itself was an uncaught exception
   from a button's click. Open questions 2, 3 and 4 at their defaults: the line in the body above the rows in the
   `.fileview-err` dress (the pane idiom the fetch and decode failures already use in the body; no rule of its own,
   the bare `.fileview-err` rule, which since the review's round 4 carries `overflow-wrap: anywhere` so that a
   message's long unbroken token breaks inside the box, and the sizes test's `BODY > div.fileview-err` chain cover it;
   outside both pairing roots, so `rawIndex` never reads it as a row and the Rendered pairing never sees it; the
   one-bar `noteBar` left free for the notices that must outlive a swap; it scrolls with the rows), one try per viewer
   around build and swap, and the button pressed with `mode()` raw. The departure from the plan's text: "under a
   `.fileview-err` line" is read as the body's own line, not the card's bar. Step 0, before any of it (A1): under node
   every suite that drives the real `openFileView` over a markdown file lived on the catch, since DOMPurify 3.4.10
   hands a module with no `window.document` the bare factory (`isSupported` false, `sanitize` and `addHook`
   unassigned), so `sanitizeMd` threw on every Rendered paint and the catch wrote the note's text into the box.
   md-sanitize.ts gains `setMdSanitizer(p: MdSanitizer | null)`, a node-only seam in the idiom of
   `installMdSanitizeHooks`'s purify parameter, read through `purifier()` (the installed stand-in, else the
   module-global DOMPurify), and every one of the 22 suites the grep names was audited (open question 17, the
   default): thirteen install a stand-in whose body follows what the suite reads (an empty body for the seam suite,
   which lays its blocks by hand; marked's markup parsed by the suite's own parser for place-memory and outline, whose
   `textContent` intercepts on `.fileview-md` are retired and whose stand-ins gained `compatMode`, `replaceWith` and a
   tree walker where a real pass needed them, the fix always in the stand-in and never a wider seam; one text node for
   text-size; the served source for edit-events), and nine open no markdown Rendered and needed nothing. The base
   tree's `sanitizeMd` calls per suite, probed in a scratch archive: 39 in the seam suite, 37 in place-memory, 23 in
   outline, 10 in undo-landed, 9 in edit-races, 7 in tracked-edit, 6 in edit-events, 4 in undo-landed-ack, 2 in
   save-busy-viewer, one in each of the three pdf suites that open the note, none in the nine untouched, text-size not
   probed since its browser legs bundle the module into a page; every one a swallowed throw before this slice. One
   fact the audit turned up: the outline fixture holds a formula heading (`Ratio $x$`), so with the seam the KaTeX
   fill runs for real over that suite's stand-in body, and the row's text is unchanged only because the formula is a
   single letter rendered as html. file-view-seam.test.ts (58, ten new in the build, three in the review's round 1,
   three in its round 2 and two in its round 3, one more in the manager's round 1 at item 6, below: A1's record pin
   that a Rendered paint sanitizes through the stand-in once per paint and never on a Raw one and that DOMPurify over
   the stand-in's window and the module-global instance are the bare factory, executed over the library; A2's two, the
   throwing stand-in giving the line first with the message, `div.fileview-code` with `code.hljs` under it, no
   `.fileview-md`, `mode()` raw, the Rendered button pressed with the preference unwritten, `renderedImages()` `[]`,
   the Outline hidden, `text()` the file's text, one paint, then the Raw click's rows without the line, a Rendered
   click that throws again bringing the line back and the healed Rendered click's `.fileview-md`, and a throw from the
   adoption after the sanitizer taking the same road with a bare string and an empty-message Error named by
   `String(err)`; the `mode()` closure and the sanitize-then-rewrite order re-pinned; items 3, 5, 6 and 7 add the
   rest), file-view.test.ts (59, four new in the build, one in the review's round 1 over the offset spender's `mode()`
   read and one in its round 2 over `fellMessage` and the catches' order, A2's being the source pin over `mdBlock`'s
   shape, both renderBody try shapes, `renderFell`, `mode()`, `RENDER_FELL` and `renderFellLine`, with the swap-line
   and `if (rendered)` pins re-aimed), file-view-links.test.ts (28, the fallback pin re-aimed: no bare-text fallback
   in `mdBlock`, the Raw rows codeBlock paints linkified by codeBlock; item 5 re-aims one adjacency pin),
   file-view-place.test.ts (8, both viewers' read, swap, folds, stamp, hooks and seat pins re-aimed to the try; item
   6's optional line allowed), md-url-view.test.ts (29, the sanitize-count pin re-aimed to one `.sanitize(` call
   through `purifier()`, the `if (rendered)` pin and the URL renderBody tail pin re-aimed; item 6 re-aims the tail to
   require its line), md-sanitize.test.ts (19, one new: the seam executed, a stand-in receiving the one profile spread
   with RETURN_DOM and its body coming back after the passes, null putting DOMPurify back, which under node then
   throws; the callers list and the count re-aimed to `purifier().sanitize(`), render-sanitize.test.ts (3, the chat
   renderer's source pin over `DOMPurify.sanitize(` in `sanitizeMd` re-aimed to `purifier().sanitize(` with the
   accessor's line pinned: a pin outside A1's audit, which listed the suites that drive `openFileView`, found red by
   the consolidation pass's full npm test), file-view-landing-throw-browser.test.ts (2 legs, both scenes re-aimed: the
   line first, the new text's rows under it, no `.fileview-md`, one more paint, `mode()` raw, the Rendered button
   pressed, `mtimeNs()` the new mtime, no uncaught error, the immediate scene going on to the Raw click and the healed
   Rendered click), file-view-place-memory.test.ts (13, the stand-in installed and the intercept retired, the marked
   import dropped), file-view-outline.test.ts (15, the same, the formula heading's row pinned as KaTeX's html with the
   fill asserted to have run; item 3 re-aims its closers case), file-view-text-size.test.ts (33, the stand-in
   installed, its browser legs included); the stand-in installed with no assertion changed in file-view-tracked-edit,
   file-view-edit-events, file-view-edit-races, file-view-undo-landed, file-view-undo-landed-ack,
   file-comments-save-busy-viewer, file-view-pdf-chunk-latch, file-view-pdf-frame and file-view-pdf-lifecycle (counts
   in the list below). Recorded by the build and closed in the review's round 1: a heading target (`at.heading`) over
   the fallback rows was spent as before by renderBody's tail and by `landTarget`, so the notice bar could say "No
   section named" under the failure line while the section existed, and the URL viewer's `landFragment` spent the
   URL's own fragment over the rows the same way. `spendHeading` and `landFragment` return while `renderFell` is set,
   the target kept for the healed Rendered paint as under a Raw preference (the seam case drives the open, a Raw
   click, a Rendered click that throws again and the healed paint that lands the section; the failures leg's fifth
   scene drives the URL viewer's fragment the same way, `## Later` landing at the body's top after the heal); the
   exact-line pin in tests/test_guide_files_place_and_outline.py stands, and the pins in file-view.test.ts and
   md-url-view.test.ts require the guard lines. From the same round: an `{ offset }` target over the fallen render
   landed nowhere and its past-the-end notice named a block, because `scrollToSourceOffset` read the pressed button
   (`fmt.md`), took the Rendered branch and found no `.fileview-md`; it reads `mode()` now, so over the rows it takes
   the Raw branch, lands on the row through the seam's `scrollToOffset` and says "line". Recorded by round 1 and
   changed in the review's round 2: after a fallback throw from a click (`mdBlock` and the fallback `codeBlock` both
   throwing, a bug and not a file) the body kept the previous paint while `renderFell` named the failure, so `mode()`
   answered raw over a standing Rendered box until the next paint, `renderedImages()` answered `[]` and the Comments
   panel's `contentRoot` rule looked for `code.hljs` over a standing `.fileview-md`; round 1 left it, reading the fix
   as a trade for the reverse mismatch on a Raw-then-Rendered click, and round 2 ruled it the feature's own edge: both
   catches compute the message into a local (`const fell = fellMessage(err)`), swap the line and the rows in, and
   record `renderFell = fell` after that swap, so a fallback throw propagates as designed with the previous paint and
   its record standing, and `mode()` answers what the body shows (the seam case: the body's `replaceChildren` made to
   throw for every swap, a Rendered click over a standing box leaving the box, `mode()` "rendered" and the rule
   finding `.fileview-md`, then the healed click, then over a standing fallback the line, the rows and the record
   staying; red over a git archive of 402f95d2d at `mode()` answering raw). The reverse case, Raw showing and a
   Rendered click that throws twice answering "rendered" over the rows because the click writes `fmt.md` before the
   paint, is main's own state, pre-existing and routed. The same round made the message `fellMessage(err)`: an Error's
   message with the sentence marked 12 appends to every message it rethrows (its `#onError`, wrapping the lexer,
   `walkTokens` and the parser: a request to report the failure to marked's tracker, with that URL) cut by
   `MARKED_REPORT_TAIL`, keyed on the sentence's text alone; its name when nothing else is left (`new Error("")`:
   "Error", as `String(err)` answers for one); any other thrown value by its string; a message with a newline of its
   own is kept whole. Before, a throw at that stage put the sentence and the URL inside romp's own line, telling the
   person to report a romp file's render failure to marked (the seam case: `marked.Lexer.prototype.lex` made to throw,
   marked's `onError` appending the sentence, the line reading the message alone, an empty message inside marked
   printing "(Error).", a message with its own newline kept whole, the healed paint rendering; red over the archive at
   the line's text). file-view.test.ts pins `fellMessage`, `MARKED_REPORT_TAIL`, both catches' three-line order and
   the count of two, and the landing hold's comment above `fetchFile`, whose list of the passes after the try that
   reject into the chain's catch named the hooks, where `fireRendered` runs each hook in its own try and swallows its
   throw (the folds' restore, the width stamp, the Outline's sync and the seat are the passes that throw through); the
   render catch pins in file-view-place.test.ts, file-comments.test.ts and tests/test_guide_files_failures.py were
   re-aimed to the three-line catch. Also recorded: `setMdSanitizer` leaves the module-global `hooksInstalled` latch
   alone, so a stand-in installed after a first `sanitizeMd` call gets no hooks (every suite installs its stand-in at
   module load, before any paint). Also recorded since the review's round 6: "the body's first child" above reads with
   one exception, an empty file whose render still threw, where item 6's line stands above this one and the rows (its
   record, with the measurements, at item 6).
2. *Item 2, the figure label.* One capture-phase `error` listener on `.fileview-body` per open, installed once at the
   open beside the body's other listeners and dropped with the viewer (`armFigureLabels`; `ctx.onClose` in the local
   viewer, the close hooks in the URL viewer, which gets the same two), the `armReseat` idiom, since an img's `error`
   does not bubble and the body hears it in the capture phase; a paired capture-phase `load` listener removes the
   label when a retry lands. The listener acts on an img inside `.fileview-md` and outside a gate's placeholder (a
   gated img has no src and never errors, and a label inside the placeholder would leave with `restore`), and parks
   `span.fv-figerr[data-fv-figerr]` as the next sibling of the anchor: the img, or the outermost `<picture>` or
   `span.fc-imgwrap` around it (the regions layer wraps THE img while the Comments panel is open, before the error
   fires, and its dispose puts the img back and removes the wrap with everything in it, so a label inside would leave
   with the panel's close; anchor-map.ts reads that span as the img, so the label's place in the block is the same to
   the map; the contract's addendum, written before the code), or, since the review's round 1, a link holding the
   figure alone (`linkAround`: an `<a>` whose one element child is the figure or its wrap and whose text is blank, a
   README's linked badge; inside the link the label wore the pointer and a click on it followed the link, and a link
   with text beside the figure keeps the label beside its img, as the browser's alt text is). The label's text is the
   exported `FIGURE_FAILED` ("Image failed to load:"), a space, the source, or since the review's round 2 the words
   "the source is empty" (`FIGURE_NO_SOURCE`, module-private) when the figure names none, and the alt in parentheses
   when it is not empty. An empty destination (`![alt]()`, which marked renders as `<img src="" alt="alt">`, or an
   authored `<img src="">`) fires the img's `error` with no request made (the HTML specification's empty-src rule);
   `figureRefs` skips the empty value, so nothing rewrote or gated it, and `failedSource` answers the empty string
   (null for a figure with no source attribute at all), which the label printed: the fact, two spaces and the alt in
   parentheses, a dangling colon and nothing named. Contract C2's formula is superseded again, `FIGURE_FAILED + " " +
   (src ? shownSource(src) : FIGURE_NO_SOURCE) + (alt ? " (" + alt + ")" : "")` with `const src = failedSource(img)`,
   and the guide's Figures sentence stands (file-view-figure-empty-source.test.ts, below; red over a git archive of
   402f95d2d at the label's words). The source, since the review's round 1, is the candidate the browser asked for
   (`failedSource`): the browser picks ONE candidate for an img, the first `<source>` of an enclosing `<picture>`
   whose media and type match, else the img's own srcset by density, else its src, and fires the img's `error` when
   that one fails with no fall back to another, so a label naming the src of a picture or a srcset img named a file
   the browser never asked for (the build's header comment had the premise wrong: a picture does not fire once every
   source fails); when `img.currentSrc` is set and is not the img's own src, the candidate is matched against the
   picture's sources and the img, candidate for candidate through `parseSrcset` over the rewritten srcset and the
   authored one that `rewriteFigureSrcs` keeps in `data-fv-srcset` (`FV_SRCSET`) beside every srcset it rewrote, and
   named by its authored spelling, or as written when the srcset was left as written (a remote host's absolute
   candidates); the img's own src, or no `currentSrc` to read (the node stand-in), keeps the panel's own `pictureDest`
   rule (`data-fv-src` when the viewer rewrote the src, else `src`). In the URL viewer the label names the resolved
   absolute URL, never the figure as written: `resolveFigureRefs` rewrites every relative src and srcset candidate of
   a URL document to an absolute URL against the document and stamps neither `data-fv-src` nor `data-fv-srcset` (the
   src stamp is the panel's pairing key and a URL document has no panel), so `pictureDest` falls to the rewritten src
   and the srcset walk names the rewritten candidate; a document at a test origin's `/notes/doc.md` holding
   `![u](figs/u-missing.png)` wears the label with that origin's `/notes/figs/u-missing.png` in full, and only a
   candidate written absolute reads as the author wrote it (the review's round 2 corrected this clause, which had
   counted a URL document's candidates among those left as written). A `data:` source is cut to its head through the
   comma with an ellipsis (`shownSource`; the first forty characters when there is no comma): a broken inline image's
   label printed the whole encoded payload, 1518 px tall at 380 px, two screens of base64 where the note should go on.
   One label per img, found by the mark and never by the class (the figure gate's rule: an author can type the class):
   a second `error`, the chat page's heal retrying, rewrites the one label's text; the img's `load` removes it. The
   img keeps every attribute and its place, `img.onerror` is never set (the heal skips an img with one), the insertion
   fires no paint hook (the body's nodes stand and the panel's marks are unaffected), and `headingWords` skips the
   mark, so a heading holding a failed figure keeps an Outline row reading its words and the alt alone. The event
   carries no status, so the label names the fact and the source, never a reason, and the viewer makes no second
   request. `fv-figerr` joins both `CONTROL_CLASSES` lists (anchor-map.ts and reader-place.ts: the label's text is the
   viewer's, not the note's, and a control's text in a block once refused the block's pairing and seated the reader's
   place fourteen paragraphs off; the slice's first HIGH risk, closed in C1c before the label existed). The sheets (B)
   key one rule on the class under the box, `.fileview-md .fv-figerr {`, in the gate's shape (inline-flex, centred, a
   1px dashed `var(--box-border)`, `var(--overlay-05)`, 0.86em, radius 6px, line-height 1.3, max-width 100%) with the
   error dress's ink `var(--warn)`, a 0.3em side margin off the alt text or the prose beside it and `overflow-wrap:
   anywhere` so a long src wraps inside the cap, without the gate's min-width, min-height and cursor (the label is not
   clicked, and no button stands in it, so the sizes test gains no chain); one line in each sheet's `@media print`
   block beside the gate's (black ink, black border, no wash); byte-equal in both sheets with the head in
   fileview-parity's list. Before the slice nothing in the Rendered box listened for an img's `error` (the media
   view's `imgBlock` armed its own img alone), so the kernel's answers for a figure that fails, a 404 for a missing
   file or a path outside its roots, a 413, a 415, a text file named as a figure that a 200 hands the decoder, drew
   the browser's broken-image glyph, wordless when the alt was empty. Open questions 7, 8 and 9 at their defaults: the
   `<img>` element (a `<picture>` through its img; video, audio and an inline svg's `<image>` recorded as a follow-up,
   the media body covering images alone), the img left in the DOM as the browser draws it with the label as its
   sibling (the panel pairs embeds by img order and `data-fv-src`, the layer wraps THE img, the reader's place counts
   `<img` tags in a row: a sibling leaves all three alone), and the words the fact and the authored src with the alt,
   no reason. The departure from the plan's text: "an inline error naming its src" is a label beside a kept img, never
   a replacement or a wrapper. file-view-figure-error.test.ts (10, new, the formula pin re-aimed in the review's round
   2, seven in the build over the seam suite's stand-in: one label after the img with the mark, the class and the
   text, the authored `data-fv-src` for a rewritten img and the src for a bare one with no parentheses for an empty
   alt; a second error rewriting the one label and a load removing it; the img's attributes, place and onerror
   untouched; `renderedImages()` still listing both; no paint hook; the label between the img and an authored
   `span.fv-figerr` without the mark, after a `<picture>` and never inside, after the layer's wrap and kept through
   its dispose, none under a gate's placeholder or outside the box; a heading's Outline row reading "Figure 3 detail";
   one error listener per open, the same after a switch to Raw and back to Rendered, gone after the close; the URL
   viewer arming and dropping the same two; a source pin over the call sites, the listeners, the mark, the text and
   the skip; the shim's projection case; and two in the review's round 1: a picture's source candidate named by its
   authored spelling, through the regions wrap too, an img's own 1x candidate, an unrewritten remote candidate as
   written, the img's own src, no currentSrc and an unmatched currentSrc keeping pictureDest's rule, a data: source of
   three thousand characters, an inline svg and a malformed URI cut to the head, and the label after a link holding
   the figure alone, beside its img when the link has text or two figures; and one in the closing pass, the two-figure
   case at this item's end), file-view-figure-empty-source.test.ts (1, new in the review's round 2: the
   empty-destination and bare-src figures beside one whose source is written, one label per img with the words and the
   alt, the positions, no paint hook, a second error rewriting the one label, and the source pins on the formula and
   the constant), file-view-figure-error-browser.test.ts (3 legs, new: two in the build, the real viewer with
   real-viewer-leg's new `serve` answering the note's figures, a 404, a text/plain body the decoder refuses and an svg
   that loads, under styles.css on the pane and in the chat modal and under feed.css: four figures, three labels with
   their authored src and alt, none on the svg, the img untouched, the label in unit B's dress, the Outline's rows
   "Report" and "Figure 3 detail", a Raw switch from the failed figure's paragraph seating on its row, and with the
   Comments panel open every figure taking a layer, each label following its wrap and none inside one, and a comment
   on the failed figure's paragraph painting its highlight, the slice's first HIGH risk measured; the chat page's heal
   installed through the leg's new `before`, three errors at the first paint, a dispatched `romp:wsup` re-fetching the
   three and the same three labels rewritten in place, every wait on the figures' `complete` or the panel's paint and
   never a timer; and the round 1 scene on the pane: the browser asked for dark.webp and missing-1x.png and never
   missing-2x.png, plot.png decoding as the plain figure, the labels reading `figs/dark.webp (plot)` and
   `figs/missing-1x.png (dense)`, a data: figure's label under 60 px tall at 900 where it was 666, and a linked
   figure's label a child of the paragraph with `closest("a")` null and no pointer cursor), fileview-parity.test.ts
   (4, the `.fileview-md .fv-figerr {` head in RULES, red over the base with no rule in either sheet; the print block
   already pinned whole), anchor-map.test.ts (43, three new in the build and two in the review's round 1: C1c's, a
   paragraph holding the label pairing with its block, the caption mapping and painting, a drag from inside the label
   landing at its edge, the label alone selecting nothing, and a label beside a bare `<img>` html block leaving the
   block after it paired; item 7's C4c case; the consolidation pass's case, below; the review's two lay the CRLF
   fixture and four small sources on the viewer's grid (`buildRawViewer`, the replica's three-ending split with the
   highlighter, and `rawDomIndexOfSplit`) and drive `paintRawPoint`, `paintRaw` and `paintChangesRaw` over them:
   sixteen rows with no ending in any, the same marks the older grid paints less its ending-only slices, every point
   on the row `rawRowForOffset` and `rawOffsetToLine` give, the selection walks equal before and after the paint; the
   nine older cases keep the LF-only grid as a standing input of the map, which assumes neither split, the build's
   open question decided so; under three painter-local mutations of anchor-map.ts the two are the only reds),
   anchor-map-fallback-markup.test.ts (25, the mirror list gaining the class, a record change),
   md-config-figure-gate-place.test.ts (1, two scenes in the readPlace walk: the label inside the block's `<p>` and
   beside the block's own text, red over the base with no place). The consolidation pass's full npm test found the
   label at the box's TOP level misaligning the Rendered pairing: when the img is a top-level node of an html block
   (`<img src="logo.png">` alone, or then `<div align="center">` in one block, a README's shape) the label is
   top-level too, `analyzeRendered` counted it among the nodes the blocks pair against, the img's block owned the img
   and the label, and with the Comments panel open (the wrap and the label ahead of the div) the heading nested in the
   div was refused as not matching the file (anchor-map-wrappers-browser.test.ts, two legs red). anchor-map.ts now
   leaves the label out of the top-level nodes (`isFigureLabel` in `holdsContent`), the label alone and not every
   control: a display formula the fill could not render at the top level is its block's node and a gated figure's
   placeholder holds the block's img, and a first cut that left out every control turned anchor-map-obsidian.test.ts
   (four formula cases) and md-config-figure-gate-place.test.ts red, so the pass narrowed it. anchor-map.test.ts's
   third new case holds it (the bare img block owning its img alone with the label after it, or the panel's wrap
   alone; the README shape's heading and paragraphs mapping with the label between the img and the div, the panel open
   or closed; red over a git archive of 7c8a1905c at the block owning [IMG, SPAN]), with
   anchor-map-cells-browser.test.ts (6 legs, one read re-aimed: the leg serves no picture, so its table's `x.png`
   fails and wears the label since item 2, and the cell's text is read with the label aside and the label's presence
   pinned). Recorded, not changed: an authored `<span class="fc-imgwrap">` around an img puts the label after that
   span rather than after the img, still beside the figure in the same block (the anchor climbs the layer's class, as
   anchor-map.ts recognises it); the browser leg's count of six error events after `romp:wsup` relies on Chromium
   firing no `error` when the heal removes the src before re-setting it (the HTML specification fires none for an img
   with no src and no srcset); the label's rendered look, the side margin against the browser's alt-text rendering and
   the wrap of a long src, is asserted by computed display, border and box width in the leg and not by eye; after
   `closeFileView` one of the Comments panel's three capture-phase `load` listeners stays on the detached body (the
   viewer's own is gone), harmless while the body is detached, so the node case asserts the count fell rather than
   reached zero. Recorded in the review's round 6 and fixed in its closing pass, two figures under one anchor: two
   imgs in one `<picture>` an author types (the sanitizer keeps it), or two imgs an author puts in one `<span
   class="fc-imgwrap">`, shared that anchor, since `figureAnchor` climbed a `picture` and the layer's class without
   asking what either held, so one label after it named the last of them to fail (the second `error` found the first's
   label there and rewrote it, the one-label rule reading per anchor) and the `load` of either removed it while the
   other still failed, leaving that figure the browser's own rendering alone, its alt text or the glyph; measured in
   headless Chromium at d617bcf67, two such imgs in one span and a bare failing control drew two labels for three
   failures, the span's naming the second figure, and healing either img of the span removed it with the other still
   at natural width 0 and no label, and the same two imgs in one `<picture>` at f2c422709 gave the same numbers. The
   closing pass read the healed pair's still-failing figure as a failure case showing a bare glyph, the third of the
   cases that reopen the review after round 6, and fixed it as the round 6 record proposed: `figureAnchor` climbs a
   `picture`, the layer's class or a link holding the figure alone only when it holds exactly one img (`oneImg`, a
   `querySelectorAll("img")` count of one), so a wrapper holding two is left as the img's parent and each img's label
   is its own next sibling inside it, naming its own source, a second `error` rewriting its own alone and a `load`
   removing its own alone; the layer's own wrap holds THE img and is climbed as before, inside a two-img `<picture>`
   included, and a link's `linkAround` already asked for one child, so every one-img figure's label stands where round
   1 left it. anchor-map.ts is unchanged and reads the label as before (`isFigureLabel` by the class, both
   CONTROL_CLASSES lists, so a label inside such a span is skipped by both text walks as one beside the img is),
   checked by its node suite and the wrappers and cells browser legs. file-view-figure-error.test.ts's tenth case
   holds it (two imgs in one picture and in one authored wrap, a label each after its own img naming its own source, a
   second error rewriting its own alone, a heal removing its own alone with the other's standing, the layer's wrap
   inside a two-img picture climbed and the picture not, a link around a two-img picture not reached; red over a git
   archive of 9553c666c at the first count, one label for the pair) with two source pins on the gate and the count.
3. *Item 3, `error()` and the hooks.* The fetch chain's `.catch` fires the hooks AFTER its swap, the `imgFailed`
   order: `body.replaceChildren(why)`, `syncOutline()`, then `viewError = msg; fireRendered();`, then
   `rearmDiskBar(my)` as before (the re-arm reads the keyboard after the paint, Slice 6's rule; a hook does not move
   the keyboard), on every failure path, a first open's included (`text()` null then; open question 5, the default).
   The seam gains `error(): string | null` (contract C1), a REQUIRED member of `FileViewActionCtx` directly after
   `mtimeNs()`: the words of the pane the body shows IN PLACE of the file (the fetch catch's `msg`, or `imgFailed`'s
   decode sentence without its hint and its Download button, read off the pane's own node before those join it); null
   while a text or media view shows, the loader included, and null over item 1's fallback rows. Closure state
   `viewError` per open, set at the two pane paints and cleared at the content paints (after the text paint's try
   closes and item 6's empty-file line, before the folds' restore, so a swap has stood, the fallback rows included,
   before the record clears, and a fallback swap that throws leaves a standing pane's words with the record, as
   `renderFell` is written after the swap: the review's round 3, where round 2 had it after the guard and before the
   pass, and a fallback throw over a standing pane left `error()` null while the pane stood; at the media arm's head
   after the loader's return, one line covering the SVG Source view, the chunk's pages, a kept frame and the frame or
   picture before `whenShown`, the pages path being a media paint the contract had not named; at the editor's entry
   before its edit-mode render), never read from the body. `text()` and `mtimeNs()` are unchanged: after a failed
   reload they answer the last landing's, and `error()` says the body shows a pane instead. The `onRendered` doc says
   a failure pane is a paint; the direct `fireRendered()` count in file-view.ts goes from seven to eight, the seam's
   count pin naming the catch. The Comments panel (C): `paintAll` reads `ctx.error()` at its head, after the editing
   early-return and `clearLanding()` (the pass's two pinned first statements; the contract's three addenda moved the
   read from the hook's own line to keep that line's pinned text), and when it answers a string while a bytes wait is
   up, `bytesFailed(words)` clears the deadline timer, drops the busy slot and puts `BYTES_FAILED` ("The file could
   not be read again") with the words in parentheses and the fixed tail (what the view shows, and Reload as the way
   out) in the "bytes" row with Reload, the shape of `bytesLate`'s row, before the pass stands down over the pane; a
   wait a later status arms while the pane stands ends at the same read. The 15 s deadline stays for the one case it
   was written for, a kernel from before this feature, whose reload can neither land nor fail through the seam; its
   comment says so. Before the slice the catch painted the pane and fired no hook, so the panel, waiting on the reload
   its poll had asked for, kept its loader up for the deadline over a body that already said what happened, and the
   seam had no member saying the body showed a pane. Open questions 5 and 6 at their defaults: every failure path
   fires, a first open's too; a required member with closure state, and the 118 hand-written stubs swept in one commit
   (C0c: `error: () => null,` beside the mtimeNs stub, 120 lines in 118 files, two chord suites holding two ctx
   literals each, every file equal to its parent once the insertion is removed, the eleven files outside the
   file-comments pattern included; committed inside a typecheck window of 94 excess-property reports that A3 closed by
   landing the member, the sequence the build's order allowed). The departure from the plan's text: `error()` is null
   over the render fallback (item 1's rows are the content; `mode()` "raw" is that paint's word), and "every failure
   path fires the paint hooks" is read as every paint that puts a pane in place of the file (the fetch catch,
   `imgFailed`, the pdf chunk's page failures), item 1's fallback firing as the text paint it is and item 2's label
   firing nothing. file-view-seam.test.ts (a failed reload: one paint, `error()` the stub's 404 words, the pane in the
   body with the same words, `text()` and `mtimeNs()` the last landing's, `mode()` unchanged, then the file back with
   `error()` null and a paint; a first open of a missing path with one paint, `error()` set, `text()` null; the two
   decode cases gaining `error()` as the pane's own sentence and null after a reload that decodes; the member, its
   placement, its doc through `docOf`, the closure line, the three clears by site, the two set sites and the count at
   eight pinned), file-view.test.ts (the catch-order pin re-aimed: swap, `syncOutline`, `viewError`, `fireRendered`,
   `rearmDiskBar`, with a pin that the hooks never follow the re-arm), file-view-reload.test.ts (23, five failure
   scenes gaining `error()` and the paint count: the first open's 404, the 404 pane under the deleted-on-disk bar, the
   deletion under the bar's own Reload, the overtaken bar ask with the poll's 404, the network failure whose `error()`
   is "network gone" with the path as the pane's hint alone; and the brief's 413 scene, added in the review's round 2
   after two rounds had left it: the suite's stub gains a GET that answers a status with a body, and a Reload whose
   GET answers 413 paints the too-large pane with the kernel's words and a Download offer, fires the hooks once at
   that paint, answers `error()` with the pane's words while `text()` and `mtimeNs()` keep the last landing's, and
   leaves the bar standing with its button armed again, the seam's own reload refused the same way painting the same
   pane with one paint and no HEAD, and the file back under the cap landing and clearing both; green at 402f95d2d and
   red at the paint count under the mutation that removes the catch's `fireRendered()`; the suite's other 413 is a
   HEAD answer that retires the probe), file-view-outline.test.ts (the closers case, which pinned a failed reload as
   no paint, re-aimed to the pane's paint with `error()`), file-view-failures-browser.test.ts (7 legs, new, shared
   with items 1, 5 and 6, two of them the manager's round 1's, at items 1 and 6: the reload scene over the real viewer
   in the pane surface, the report removed from the page's docs and `__seam.reload()`, the paint count growing by one
   at the pane's paint, `error()` the stub's words, the pane the body's child with the same words, `text()` and
   `mtimeNs()` the last landing's, then the file back under a new mtime with a paint and `error()` null),
   file-comments-changes-review2.test.ts (23, a third scene beside the deadline one: the deferred reload fails, the
   loader goes at that paint with no timer tick, the row shows the seam's words in the fixed shape with Reload,
   nothing is marked over the pane, a later tick of the deadline raises no second row, a status landing over the
   standing pane arms no loader, Reload re-fetches and the landing clears `error()` and repaints the marks, and a
   probe hook recorded no swallowed error, the medium risk on firing the hooks from the catch; and the review's round
   1's two scenes: a landing whose bytes fail to decode with the status's mtime already under the pane, in the text
   stand-in with the media landing's order and over a media seam, the loader gone and the row standing with the pane's
   sentence and Reload through a status and the deadline's tick until the row's Reload lands bytes that decode; and a
   Raw or Rendered click repainting the earlier text over a standing failure row, through a `repaint` member of the
   suite's world, the row's tail flipping to the deadline row's words at the repaint, a second repaint and the tick
   leaving it, the Reload failing again filing the failure row anew and the landing taking it away; and the review's
   round 2's four scenes, below: a landing of text newer than the status's taking the row away, a reload the panel did
   not ask failing again over the flipped row, the row's Reload whose status lands first over the standing pane and
   whose fetch is then refused for other words, and Edit clicked over the pane; and the review's round 4's two scenes,
   below: the row's Reload over a pane whose fetch never answers, the loader standing to the deadline row at 15 s, and
   the poll's fetch on a new mtime over a standing pane), file-comments.test.ts (35, the seam's member list gaining
   `error(): string | null;`, the swap-line pin re-aimed to contract C7's try shape, `mode()`'s closure pinned to read
   `renderFell`; red over A2's tree until C2c, the window both commits name), and the 118 swept files (one line each,
   no assertion changed; four run as a sanity check). The panel scene the brief named for the failures leg was added
   by the consolidation pass (C2c having landed after A3): the Comments panel open over a seeded comment, a status
   whose file mtime moved (the page's table, asked by the panel's reopen) has it ask the reload and hold its loader;
   the reload fails, and within two frames of the pane's paint the loader is gone and the "bytes" row reads the seam's
   words with Reload, nothing marked over the pane, `error()` the pane's words and `mtimeNs()` the last landing's; the
   row's Reload over the file put back lands the bytes and the comment's highlight is painted again (red at the loader
   over a git archive of the branch with the panel's read of `error()` removed). That scene found an ordering hole in
   the browser: the row's Reload sends the status ask and the fetch together, the status lands first over the standing
   pane, and the pass filed the failure row again (C3's standing-pane clause, which since the review's round 4 stands
   down while a fetch of the panel's asking is out, `reloadOut`, below); the fetch then landed and nothing cleared the
   row, which stood over the new text until dismissed. The pass fixed it in file-comments.ts: `bytesLanded`, the
   landing paint that shows the status's text, also deletes the "bytes" row (the deadline's as well as the failure's;
   the landing is the event the row was waiting for), no render of its own; file-comments-changes-review2.test.ts's
   third scene gained the browser's order (the status answered before the fetch lands; red at the row's count over the
   tree before the fix, 14/15). The review's round 1 narrowed the clause to a content paint (`error()` null): a
   picture's landing moves `mtimeNs()` to the new mtime before its bytes decode, so under the decode pane
   `textCurrent` was true and the clause deleted the row `bytesFailed` had filed at the head of the same pass; with
   `error()` set a wait can only have ended at that head, so nothing is lost. Round 1 added `bytesPaneGone` on the
   clause's other branch (`error()` null, the view's mtime not the status's): a Raw or Rendered click repaints the
   last landing's text in place of the pane while the row says the view shows the failure, so the row kept the seam's
   words and took the deadline row's tail. The review's round 2 replaced it with `syncFailedRow`: `bytesFailed`
   records the seam's words and the view's mtime at the paint that filed the row (`failedRow`), and every pass, the
   editing branch included, reads the standing failure row against the paint. A view mtime that is not the recorded
   one is a landing since the failure (the row's own Reload, the disk bar's, the poll's, a save's) and the row goes,
   whatever the status says of that text (before, a landing of text NEWER than the status's flipped the row to "the
   view still shows the earlier text" over the new text, until the status at that mtime landed and `bytesLanded` took
   it). The same mtime under a pane gives the row the pane's CURRENT words and the failure tail (a pane back over the
   flipped row with no wait armed, the disk bar's Reload failing again, kept the text tail before; and a fetch the
   panel did not ask, refused for another reason, a 404 pane replaced by a 413, left the earlier words under the new
   pane; until the review's round 4 the row's own Reload reached this too, its status landing first over the standing
   pane and the head filing the row off that pane's words, where the head now stands down while the panel's fetch is
   out and the new pane's paint files the row). The same mtime under a content paint, the editor's entry included (the
   editing early return reads the row after `afterPaint` and before its render, so Edit clicked over the pane, offered
   because the gate reads the last landing's text and mtime, gives the row the text tail at the entry rather than at
   the exit's repaint; a save under the editor moves the mtime, so the exit's repaint takes the row away), gives it
   the deadline row's tail. A deadline row is left as it is (its tail over a pane is pre-existing and untouched), and
   no render of its own. The four scenes are red over a git archive of 402f95d2d at "the landing answers the row",
   "the row says the view shows the failure", "the row carries the pane's CURRENT words" and "the row says the view
   shows the earlier text"; file-comments-behavior.test.ts (22) re-aims the pass's first-line pin over the editing
   branch. The review's round 4 changed the head's clause: `reloadOut`, set by `reloadView()` (the one door for every
   re-fetch the panel asks: the row's Reload, `askReload`, the re-read after an edit over moved bytes) and cleared by
   the viewer's next paint other than a reflow (the onRendered hook's paint branch, before the pass), makes the head
   stand down while a fetch of the panel's asking is out (`if (failed !== null && this.bytesWait && !this.reloadOut)
   this.bytesFailed(failed);`), so the row's Reload over a standing pane, whose status lands before its fetch, keeps
   the wait's loader and files no row off the pane that stood before the click; the fetch's own paint settles the wait
   (a landing, `bytesLanded`; a pane, the head's clause in that pane's words; nothing, the 15 s deadline,
   `bytesLate`), and `refresh(slot)`'s end leaves the "bytes" busy mark to the wait when one is armed (`if (mark &&
   !(mark === "bytes" && this.bytesWait)) this.busy.delete(mark);`), so a fetch that never answers reaches the
   deadline row (before: the row re-filed at once in the standing pane's words, the loader gone before the eye saw it,
   and the deadline cleared with the wait; the round 1 paragraph's observed loss of the loader over the earlier text,
   the same `finally`, goes with it). `bytesLanded`'s clearing and `syncFailedRow`'s pane-words clause still answer a
   row filed with no fetch of the panel's out (a later status over the standing pane; the disk bar's Reload landing or
   failing for other words). Two edges recorded, not changed: a fetch the panel did not ask (the disk bar's Reload,
   the viewer's own) over a standing pane is invisible to the panel, so a status arming a wait during it still files
   the row off the standing pane at once (a seam member telling the panel a fetch is out, in file-view.ts and the 118
   stubs, would be the fix, a follow-up); and a stalled fetch over a pane now reaches the deadline row, whose tail
   over a pane, "the view still shows the earlier text", is the pre-existing sibling recorded above.
   file-comments-changes-review2.test.ts (23) gains two scenes (the stall: the loader through the status, no row off
   the standing pane, the deadline row at exactly 15 s, its Reload's landing clearing it; the poll's `askReload` on a
   new mtime over a pane: the loader, no row, the row in the new pane's words at that pane's paint, a landing clearing
   it) and re-aims three (the reject test's browser-order tail, the format-click test's landing tail, the
   standing-pane test, retitled), each red over a `git archive` of 9c4fceac5 at the assertion naming "before round 4";
   the hook's one-line pin is re-aimed in file-comments-behavior.test.ts (22), file-view-text-size.test.ts (33) and
   tools/file-review-plan-anchors-states.test.mjs (5), and the edit-end re-read's pin in
   file-comments-editing-moved-latch.test.ts (4). Recorded, not changed, one of them since hoisted as its clause says:
   a hook a later panel registers after a first-open failure's paint hears nothing (the low risk; the seam case pins
   one paint); the media arm's one clear covers two sites the contract named and the pages path it did not;
   `imgFailed`'s sentence was read off the pane's node rather than hoisted to an exported constant, so the guide did
   not pin it (its wording predates the slice), until the manager's round 1 hoisted it as the exported `DECODE_FAILED`
   ("this image failed to decode: it may be mid-write or truncated", the old literal's dash a colon under the rule for
   added lines, the words otherwise as they were) for the guide's Figures sentence and its pin, `error()` still
   answering the sentence alone (file-view-seam.test.ts's decode case reads `error()` against the export and its
   source pin the assignment and the export line, as file-view.test.ts's does; red over a git archive of 98859d061
   with the export undefined); the reload suite's 413 was a HEAD alone until the review's round 2 added the GET scene.
4. *Item 4, the BOM.* Both save doors put the BOM back, keyed on the disk read each already makes and never on the
   client's word (contract C4; open questions 10, 11 and 12 at their defaults): when the bytes the save read from disk
   begin EF BB BF and the content the request carries does not begin with U+FEFF, the door writes U+FEFF ahead of the
   content; a content that already begins with U+FEFF is written as it is and nothing is shifted; a file whose bytes
   lack the BOM gains none; no request carries a `bom` argument and none is read (the saveFile frame, the save verb's
   args and its fence unchanged). Kernel (D1): `_save_file` re-prepends after its UTF-8 check over `cur`, counts the
   three bytes against `_TEXT_MAX_BYTES` in a second comparison after the read (the first, over the content alone,
   stays ahead of the stat and the read, as the hardening tests require), and `prior` gains `"written"`, the text as
   written, beside `"bytes"` and `"ns"`; `_edit_log_after` diffs `prior["bytes"]` against `prior["written"]` when
   present (else the frame's content), so the entry shows no first-line change and `bytesAfter` equals the bytes on
   disk; the 2-tuple return, the `fileSaved` reply and the frame handler are unchanged. Host (D2): `doSave` computes
   `content` (U+FEFF plus `a.content` when the rule holds) and `suggestions` (every submitted record whose `from` is
   an integer moved by one into the host's coordinates, `browserHint`'s rule applied to a whole save; another shape
   passes to `fitRecords` untouched, to be named there) once, after `checkIsText` and before `checkContentText`, and
   every later read (`checkTooLarge`, `fitRecords`, `editDiff`, `bytesAfter`, `editShift`, `checkReplyFits`,
   `prepareFileWrite`, `stageSidecar`, `settleLanded`, the reply's text) uses them, so one coordinate system runs
   through the save: the file keeps EF BB BF, the records fit (no `desync`), the fingerprint is over the BOM text, the
   entry shows no first-line change, `bytesAfter` equals the file's size, and the reply's `bom` is true with its hunks
   one ahead of the view as `status`'s are; the reject door, which writes over the host's own text, is a control.
   Panel (C3c): `paintChanges` hands the painters `curFrom - off`, `curTo - off` with `off = s.bom ? 1 : 0`, the rule
   the four existing sites use (the painters' `newText` check still refuses a batch whose text differs, so nothing is
   ever marked one off); `begin()` hands the editor `viewRecords(seed.records, off)`, each record whose `from` is an
   integer moved by `-off` into the view's text, a copy, while `editSeed.records` keeps the host's own records, so the
   moved-records compare reads host against host and raises no false CHANGES_MOVED row on a BOM file; the records a
   Save sends are the editor's in the view's coordinates, with no shift by the panel and no flag, the host moving each
   `from` back when it re-prepends, once per leg (a shift applied twice on one leg, or on `bom: false`, paints marks
   one character off and the painters refuse them, the slice's third HIGH risk; the e2e case runs Edit and Save end to
   end over a BOM file with the real host and asserts the sidecar's `from` values). Before the slice the host kept the
   BOM in its text and said so as `bom` in every status, four panel readers mapped by it, but the change-mark paint
   pass and the editor seed did not (on every BOM file the painters refused the batch and the changes stayed
   card-only, and the seed's marks sat one character off), and both save doors wrote the browser's BOM-less text, so a
   save dropped the file's first three bytes and both doors logged the drop as a line-1 edit. The departure from the
   plan's text, recorded as the plan's clause superseded by the earlier review's mechanism: the plan's "the host
   strips the BOM and the kernel re-prepends it on save" dates from before the `bom` bit reconciled the offsets;
   stripping in the host would move every stored `anchorAt`, `from` and `placed.at` of existing sidecars on BOM files
   by one and make the sidecar's fingerprint disagree with the vendored CLI's, so the clause is read as "the browser's
   and the host's offsets agree", with the host's text kept, and the store format is untouched (a BOM file's sidecar
   keeps its coordinates and its fingerprint). Nothing is said in the UI about the BOM: a kept BOM is not a failure.
   The kernel's change is Python the kernel runs, so the live dashboard's kernel picks it up only at the live kernel's
   restart, the manager's step after the landing. tests/test_savefile.py (26, eight new: six in the build in a class
   of their own, which since the manager's round 1 reads its BOM file and the cap edge's two offsets from
   tests/fixtures/file_comments/save-doors.json, the fixture the host's suite reads too, so the two doors' pins are
   over one fixture; and two in that round in a second class, `EditLogDiffLineEndings`, item 7; the six: a BOM file
   saved with content lacking U+FEFF still begins EF BB BF with the rest the content and the returned mtime the
   written file's; a content already beginning with U+FEFF not doubled and a file without a BOM gaining none, the
   controls; `prior` handing out the text as written on a BOM file and a plain one, the log's summary over it diffing
   `@@ -3 +3 @@` with no U+FEFF and `bytesAfter` the file's size; the three bytes counting against the cap, refused at
   cap minus two and written at cap minus three; the saveFile frame putting the BOM back and acking the written file's
   mtime), tests/test_kernel_file_comments_save.py (24, two new e2e cases over the real-host world: D1's saveFile
   frame over a tracked BOM file, the bytes, the mtime, the edit entry's diff with no line-1 hunk, `bytesAfter` the
   file's size and the owning session's trace, plus the fact that a status with no sidecar answers `bom` false since
   the host stats the file and reads no text there; D2's save verb with the view's text and the editor's records
   seeded minus one, the bytes beginning EF BB BF, `bom` true, the sidecar's `from` one on with its fingerprint equal
   to the CLI's over the BOM text, the hunks one ahead of the view, the edit entry's diff the kernel's shape with no
   first-line hunk, and the session's next track-edit reading the records as they are with nothing detached),
   tests/test_kernel_file_comments_hardening.py (31, the exact-dict pin on `prior` gaining the `written` key, one
   assertion in a file no unit owned, claimed in the build's claims file first),
   tools/file-comments-host-save.test.mjs (19, five new: three in the build, the BOM save over view-coordinate
   records, the bytes, the record one on with its anchor rebuilt over the BOM text and the CLI's fingerprint, `bom`
   true with the hunk one ahead and a status after it agreeing, the entry with no first-line hunk, the next track-edit
   fitting with nothing detached; the reject door keeping the BOM as a control, green before; a content already
   carrying U+FEFF written as it is with records unshifted, and a plain file untouched with `bom` false; and two in
   the manager's round 1, the cap edge through the host door over the shared fixture's `bomCapEdge` and item 7's
   line-ending parity case, both below), tools/file-comments-host-tiebreak-review.test.mjs (12, its BOM scene
   rewritten in the manager's round 1, below), tools/file-comments-host-untouched.test.mjs (9, the doSave order pin's
   `stageSidecar` line re-aimed from `a.content` to `content`), file-comments-changes-review.test.ts (12, the BOM case
   flipped: with `bom: true` the shifted hunks paint, "cut" in Raw and the insertion in Rendered; the same hunks with
   `bom: false` or no word still refused, card-only with Reveal, the control; unshifted hunks under `bom: true`
   refused, the shift exactly one applied once), file-comments-about-fixes.test.ts (8, the BOM case's row holding
   three marks, h1's point and tint and h2's tint, where it held none and the brief expected one; the row's text nodes
   read under the marks), file-comments-editing-races.test.ts (14, one new: a BOM file's seed carrying the records
   with `from` one back as a copy, a status with the same sidecar under the editor raising no head row, Save sending
   the editor's records unshifted with no flag, and the control without `bom`), tests/test_file_view.py (22, one
   record pin: `_decode_text` over EF BB BF plus "hi" keeps U+FEFF as the first character, the served shape the
   browser's fetch strips, and `b""` decodes to ""). Recorded by the build and closed in the review's round 1:
   Reveal's scroll and landing cue (file-comments.ts, the fcreveal branch) and the card's line suffix through
   `rawOffsetToLine` read the host's offset unmapped on a BOM file, one character off and a row off exactly when the
   change sits at a line's ending (the mark on row N, the Reveal and the title on row N+1), and the change cards'
   paragraph groups (`changeView`) read the host's offsets over the view's text, so such a change grouped under the
   blank line after its paragraph, titled "line N+1", or under a line past the file's end; every panel read of the
   host's offsets maps by `bom` now, the Reveal through one `from` (`c.curFrom` less one on a BOM file, computed ahead
   of `revealInRaw`, so the switch still precedes the scroll and the scroll the cue), the suffix by the same
   subtraction, and the groups over the host's text with the U+FEFF put back ahead of the view's (`paragraphAt` over
   it is the host's paragraph, the title's trim strips the mark with the other whitespace, the line count sees no
   ending in it; file-comments-model.ts unchanged). file-comments-reveal-landing.test.ts's three BOM cases: a deletion
   at the end of line 6 and one at the file's last ending scroll to, cue and title lines 6 and 10 with the groups
   under their paragraphs and the blank line 7 clean, the marks off and on, and the control without the bit;
   file-comments-reveal-title.test.ts's BOM case reads "(line 6)" where the base read "(line 7)". Recorded, not
   changed, two of them since tested or rewritten in the manager's round 1 as their clauses say: a status on a file
   with no sidecar answers `bom` false because the host reads no text there, so the bit is trustworthy only once a
   sidecar exists (pinned as a fact); both doors apply the rule to the read their mtime fence guards, so a file that
   gained or lost its BOM between the read and the save refuses `changed on disk` or `file-moved` before the rule
   runs, not separately tested; the host's `checkTooLarge` counts the BOM like the kernel's second comparison (since
   the manager's round 1, tools/file-comments-host-save.test.mjs drives the edge through the host door over the same
   fixture the kernel pin reads, save-doors.json's `bomCapEdge`: refused too-large with nothing written at cap minus
   two, written at exactly the cap with EF BB BF first at cap minus three; red with the host's cap check put back over
   the view's text alone); the host's tiebreak suite's BOM scene, which stood in for the editor's save with a raw
   write that dropped the BOM, drives the save verb since the manager's round 1 (the view's text saved, the file
   keeping EF BB BF, the write stamping the comment on the copy under its stored heading path one offset on, fields 3
   of 4, nothing left in `placed` on the reply or the next status, and a write from outside the viewer that dropped
   the BOM confirmed by the stamped ordinal, a control leg labelled as such; red over a git archive of main 462ad3ccf
   at the reply's `bom`); and a file whose bytes begin with two BOMs (EF BB BF twice, a tooling artefact) loses one on
   every save through either door while its edit entry shows a first-line hunk over a line nobody touched (the
   review's round 4, low): the browser strips exactly one U+FEFF (Chromium 151, measured over a routed double-BOM
   body: `fetch().text()`, the Response constructor and TextDecoder agree, where node's undici strips both), so the
   view begins with the second and the save's content begins with U+FEFF, which the rule writes as it is (the kernel
   door probed under the test floor: a 29-byte double-BOM file saved with nothing typed comes back 26 bytes with one
   BOM and one hunk, the first line's two U+FEFF against one; a one-BOM control 26 to 26 with an empty diff), and the
   bytes written are the base's (462ad3ccf has no BOM rule in either door). Pre-existing and inside the never-doubled
   clause above; a comment at the kernel's rule names the shape; the exact form, if wanted, keys each door on its disk
   read alone (a BOM read means one U+FEFF written ahead of whatever the content begins with), at the cost of the
   never-doubled control in tests/test_savefile.py and tools/file-comments-host-save.test.mjs, which would then write
   two BOMs for a content carrying its own U+FEFF over a one-BOM file.
5. *Item 5, the Latin-1 line.* The fetch's `Verdict` gains `notUtf8`, true when the Content-Type starts with
   `text/plain` AND `X-Romp-Text-Utf8` is exactly "0" (never `!isText`: an image or a PDF carries no header at all,
   and an old kernel that sends none leaves `isText` true with Edit off through `!mtimeNs`), read with the other
   headers and applied with the other verdicts at the landing. At the text landing, after `text = t` and
   `renderBody()` and BEFORE `landTarget()`, a "0" file raises `noteBar(LATIN1_NOTICE)` ("This file is not UTF-8 on
   disk, so it can be read here but not edited: a save would rewrite its bytes as UTF-8.", shown alone in the bar):
   before `landTarget` so an open's own target notice takes the row under the one-bar rule, being the answer to the
   person's own click (the past-the-end line notice is raised inside `landTarget`; the offset and missing-section
   notices a frame later); a reload's landing has no target and raises the line again, after `settleDiskBar` has
   dropped the changed-on-disk bar, so a Reload brings it back. The Edit gate line is unchanged, so its three pins
   stand, and the kernel changes nothing (D3's record pins rest the line on the served "0"). Before the slice the gate
   hid the button on that verdict with no word to the reader, the one "Edit off with a reason" shape putting the
   reason on a visible button's title. Open question 13 at its default: the raise before `landTarget`, the re-raise at
   every landing whose header says "0" after `settleDiskBar`, and the ranking of notices the recorded follow-up.
   file-view-seam.test.ts (the stub's disk entry gaining `utf8?: "0" | "1"`; a text file served "0": the bar the
   card's child directly above `.fileview-main` with the words and no button, Edit hidden, `text()` the text,
   `error()` null, `mode()` raw, one paint; a reload of the same bytes leaving that element standing with one notice
   (a fresh bar before the manager's round 1); the changed-on-disk bar taking the row on a window focus over a moved
   mtime and its Reload's landing bringing the line back over the new text as a fresh element; a "1" file raising
   nothing and arming Edit; an image raising nothing; and a target's notice winning, an open at an offset past the end
   showing the line at the landing and the offset notice a frame later, a reload bringing the line back; the brief's
   line-400 case is not drivable in that stand-in, which parses no innerHTML, so the order is pinned at source and the
   real case runs in the browser leg), file-view.test.ts (the landing pin re-aimed around the raise; a source pin over
   the Verdict shape, the header read of the VALUE "0" with the text type and never a negation of `isText`, the
   application line before `settleDiskBar`, the per-open flag, the landing's order of paint, raise and spend, one
   raise site, the gate unchanged), file-view-links.test.ts (the same adjacency pin re-aimed),
   file-view-failures-browser.test.ts (the item 5 scene over the real viewer, pane and chat, through real-viewer-leg's
   new per-path header table: a "0" document's bar reading the words above the body row, in the card and on screen at
   scrollTop 400, no button, Edit hidden, the text painted with `error()` null; a window focus over a moved mtime
   raising the changed-on-disk bar in its place and its Reload's landing bringing the line back over the new text; a
   reload of the same bytes leaving the element in place, a stamp set on it before the reload still there after; an
   open at line 9999 in Raw showing the past-the-end notice and not the line, a reload bringing the line back),
   tests/test_kernel_preview.py (31, two record pins: a file holding the bytes "caf", E9, " line" and a newline
   answering 200 text/plain with the body re-encoded as UTF-8, `X-Romp-Text-Utf8` "0" and the body's Content-Length,
   its HEAD answering 200 with no `X-Romp-Text-Utf8` and the size on disk, one byte short of the GET's body; a
   zero-byte `.md` answering 200 with an empty body, "1", Content-Length 0 and the mtime header, its HEAD 200 with
   length 0, item 6's fact). Recorded by the build and closed in the review's round 1: a reload's landing that brought
   a file re-saved as UTF-8 raised no line and removed none, so a Latin-1 line standing from the previous landing
   stayed until the next notice while Edit reappeared (the gate reads `isText`); `dropLatin1Line`, called right after
   `settleDiskBar` at every landing whose header does not say "0" (text and media alike), removes the standing notice
   when its words are `LATIN1_NOTICE` and leaves a target's notice or the changed-on-disk bar standing in the row
   alone (the seam case: a "0" open, a "1" reload with no bar and Edit shown, a "0" reload bringing the line back, and
   an offset notice standing on a "0" open surviving a "1" reload; the raise line is unchanged, so its pins stand).
   The review's round 2 added the second call site: the fetch chain's catch runs `dropLatin1Line()` after
   `closeOutline()` and before the pane's swap, so a "0" file whose next fetch is refused (a 404 after a deletion, a
   413 after a growth past the cap, a network failure) shows the pane with no line over it, where before the line
   saying the file could be read here stood above a pane saying it could not be until another notice replaced it, and
   a later "0" landing raises it again (the seam case: a "0" open, a 404 reload through `ctx.reload()` with no notice
   bar over the pane, `error()` the pane's words, Edit off and the hooks fired, a "0" landing bringing the line back,
   a 413 reload's pane with Download and no line; red over a git archive of 402f95d2d at the bar over the pane;
   file-view.test.ts pins the two call sites and the catch's order). The review's round 3 closed the state that drop
   left, where after the pane a Raw or Rendered click on a Latin-1 `.md` repainted the earlier text (the pre-existing
   repaint of the last landing's text, the viewer half of item 3's flipped row) with no line over it and Edit still
   off until the next "0" landing: a format pick (the bar's Rendered and Raw buttons and the seam's `setMode`, through
   one helper, `pickFormat`) whose paint puts the last landing's text back over a failure pane raises the line again
   when the header said "0" and no other notice holds the row (a re-armed changed-on-disk bar keeps it; a pick over
   content raises nothing, and a landing raises its own), keyed on the pane the paint replaced (`viewError` read
   before the paint, null after it) and the landing's header, never the body or a timer; two raise sites now, the
   landing's line unchanged and the pins that counted one raise site re-aimed to two (the seam case: a "0" open, a 404
   reload, the Raw click with the line back over the text and Edit off, the Rendered click raising no second bar,
   `setMode` over a second pane, the changed-on-disk bar re-armed over a pane keeping the row through a Raw click, its
   Reload's landing raising the line, and a UTF-8 note's repaint raising nothing; red over a git archive of 75ad5d042
   at the Raw click; file-view.test.ts pins the helper, its two callers and the counts,
   tests/test_guide_files_failures.py the two raise sites and the pick's gate). Recorded by the build and fixed in the
   manager's round 1: every re-raise was a new `role="status"` element, so assistive technology heard the sentence
   again at every Reload and at every poll-driven reload of the Comments panel; a text landing that finds the Latin-1
   line already standing with the same words leaves that element as it is (`latin1LineStands`, read at the landing's
   raise alone), so the live region is announced once per change and not per landing, while the disk bar's Reload
   drops its bar first (`settleDiskBar`) and that landing raises afresh, new information, and `pickFormat`'s raise,
   which already required an empty row, is unchanged (the seam case asserts the same element after a same-bytes reload
   and a fresh one after the bar; the failures leg stamps the element and reads the stamp back after a reload; red
   over a git archive of 98859d061 at a fresh element; the pins in file-view.test.ts, file-view-links.test.ts,
   file-view-outline.test.ts and tests/test_guide_files_failures.py re-aimed to the guarded line). The notices'
   ranking and de-duplication stay the recorded follow-up.
6. *Item 6, the empty file.* In the text paint, when `text === ""`, the body holds one `.fileview-err` line with the
   exported `EMPTY_FILE` ("This file is empty.", the one constant of the slice with its own terminal period: the line
   shows it alone) ABOVE the block the view would paint (the empty `div.fileview-code` or the empty `.fileview-md`),
   in both views and in the URL viewer's `renderBody` too (its document read through capped-read.ts can be ""), by one
   optional line between the try's close and the folds' restore, `if (text === "") body.prepend(emptyFileLine());` in
   the build and, since the manager's round 1, a ternary on the answer's byte count in that line's place (below). A
   prepend, so the line is a sibling of the root, never inside `code.hljs` and never classed `fv-cl`: the anchor map's
   `rawIndex` still sees zero rows over "" and accepts them, the Rendered pairing sees no block, the reader's place
   ignores a sibling above the code root. `text` stays "" and never null (null means not landed, to the seam and the
   panel; `text()`'s doc says so now); the Edit gate is unchanged, so Edit shows and the editor mounts over ""; the
   Outline button hides through `syncOutline`; `error()` is null (the content, all none of it, shows); `mode()`
   follows the buttons; a reload that lands bytes repaints without the line and one that lands "" again brings it
   back. Keyed on the text the landing applied, and since the manager's round 1 on the answer's byte count for the one
   question the empty text cannot answer (below), never a timer; no CSS (the bare rule and the sizes test's chain
   cover it); the kernel changes nothing. Before the slice a zero-byte file painted zero Raw rows or an empty Rendered
   box and nothing else, a blank pane with Edit shown, and a Rendered offset landing over it scrolled nothing and said
   nothing (the Slice 6 PR body's open ruling, the case that matters, closed here for the empty file; a non-empty
   source with no blocks is rare and stays recorded). Open question 16 at its default: one line in the body above the
   empty root, both views and the URL viewer, Edit still shown, `text` "" and never null, not the bar.
   file-view-seam.test.ts (three cases: an empty `.md` with the line as the body's first child, the exported sentence
   alone, outside `code.hljs`, not a row, no button, no hint, above the empty `.fileview-md`, `text()` "", `error()`
   null, `mode()` rendered, Edit shown, the Outline hidden, one paint, no bar, then the Raw click's line above
   `div.fileview-code` with zero rows and `mode()` raw, Rendered again, a reload landing text repainting the box alone
   and one landing "" again bringing the line back; an empty `.txt` with the line above the empty rows' root, `mode()`
   raw, no Outline button, Edit shown, and a reload landing text repainting without it; and, since the manager's round
   1, the case that was a record pin, re-titled: a `{ line: 2 }` open of an empty `.txt` raising the one-line notice
   in the bar with the line still above the empty rows' root, one notice and no button, an offset open raising the
   offset notice a frame later as worded today; and a fourth case from that round, the BOM-only file: a `.md` of one
   U+FEFF served under Content-Length 3 painting `BOM_ONLY_FILE` as the body's first child above the empty box,
   `text()` "", `error()` null, Edit shown, `mode()` rendered, no bar, Raw keeping it above the rows' root, a reload
   of zero bytes painting `EMPTY_FILE`, a reload of U+FEFF plus text painting no line with `text()` the mark-stripped
   text, and a `.txt` of the same bytes saying the same), file-view.test.ts (a source pin over the constant's text,
   the builder's shape, the two call sites, since the manager's round 1 each a ternary on the byte count with
   `BOM_ONLY_FILE`'s export and builder pinned beside them, the Verdict's `bytes` off Content-Length and the landing's
   `textBytes`, and their place after the try's close and before the folds' restore in both viewers, the builder and
   its two calls the only sites, `text = t` as it came and never null-coerced, the Edit gate unchanged, `text()`'s doc
   sentence, no row class, no trim, the byte count deciding only which words the empty text gets; the URL viewer's try
   pin allowing the optional line), md-url-view.test.ts (the tail pin re-aimed to require the URL viewer's line, the
   suite driving no real open), file-view-place.test.ts (the URL viewer's order pin allowing the optional line, a
   record change), file-view-failures-browser.test.ts (the item 6 scene, pane and chat, through real-viewer-leg's new
   `waitFor` selector, since a scene whose first paint is a line or a pane has neither paragraph nor row for the
   default wait: the line's words, its place above the empty box with zero blocks and rows, Edit shown, the Outline
   hidden, `error()` null, `text()` "", `mode()` rendered, no bar, the pane's dress by a computed colour equal to a
   probe painted `var(--warn)`, the Raw click putting it above the rows' root with zero rows, a reload landing text
   painting the box alone, one landing "" bringing the line back, and the URL viewer over an empty document showing
   the same line above the box and, after Raw, above the rows' root; and the manager's round 1's scene on the pane: a
   real `Response` of one U+FEFF reading back Content-Length "3" and text "" in the page, the `BOM_ONLY_FILE` line in
   the empty file's place with the pane's dress, `EMPTY_FILE` after a zero-byte reload, no line after text, and the
   URL viewer over a BOM-only document painting the same line, Rendered and after Raw), tests/test_kernel_preview.py
   (item 5's second record pin, above). Recorded, not changed: an `{ offset: n > 0 }` open of an empty note says "past
   the end of this file, which has 0 characters; showing the last block." a frame after the paint while nothing shows
   under the line, the Slice 6 wording, accepted as recorded in the manager's round 1 (the clause drop the line notice
   below makes is a one-line option for symmetry). Fixed in that round: a `{ line: n }` open of an empty file raised
   no notice at all, `scrollToLine` returning over zero rows, where an offset open raised one; it raises the same
   one-line notice now, before the zero-rows return, "Line n is past the end of this file, which has 0 lines.", with
   no last line to show, so the tail names one only when a row exists (the seam case above; file-view-links.test.ts
   pins the shape; red over a git archive of 98859d061 with `EMPTY_FILE` alone where the bar was expected). Also fixed
   in that round, a case the build's words did not cover: a file whose only bytes are a UTF-8 BOM said "This file is
   empty.", since the browser's decode strips the one U+FEFF the kernel serves and the line keyed on `text === ""`; it
   says "This file holds only a byte order mark." (`BOM_ONLY_FILE`, the manager's words, in the empty line's shape and
   place), the paint telling the two apart by the answer's byte count, the kernel's Content-Length read into the fetch
   `Verdict` as `bytes` and applied at the landing as `textBytes` (0 for an empty file, which
   tests/test_kernel_preview.py already pins; UTF-8 bytes that decode to nothing yet number more than zero are exactly
   the three of a BOM), the URL viewer using its streamed read's own count (`readTextCapped`, whose decoder strips the
   mark the same way); an answer with no Content-Length (a kernel from before the header, a proxy that dropped it)
   keeps the empty file's words; `text` stays "" with Edit shown, and a save writes the bytes back through the doors'
   BOM rule (item 4); no kernel change (the seam case and the failures leg's scene above; real-viewer-leg.ts's page
   stub answers Content-Length as the kernel does, and the seam stub answers it and strips one leading U+FEFF in
   `text()` as Chromium does; red over a git archive of 98859d061 at the export and at `EMPTY_FILE` painted; the
   guide's sentence follows the empty file's). Recorded still: a server answering 200 with no body at all takes the
   URL viewer's existing no-body fail path, not this line; the Comments panel over an empty file is driven in the
   browser scene alone (no page error over the empty body) and the brief's optional anchor-map control over zero rows
   is item 7's C4c case. Recorded since the review's round 6, not changed: a render that throws over "" stacks two
   lines, this one first and item 1's `RENDER_FELL` line second, over the empty rows' root, since the prepend runs
   after the catch in both viewers; only a sanitizer or DOM-pass fault throws over "" (marked and DOMPurify accept the
   empty string, DOMPurify walking a `<!-->` stand-in for it, so a sanitizer fault reaches the render), and measured
   in headless Chromium at d617bcf67 with DOMPurify's node iterator made to throw, the pane and the URL viewer showed
   the two lines in that order over zero rows and no page error, and the pane, the viewer with a seam and an Edit
   button, `mode()` raw, `error()` null, `text()` "", Edit shown and one paint (the paint count is the seam's, so the
   URL viewer gives none), the Raw click leaving this line alone over the rows and a healed Rendered click this line
   over the empty box, the same order from a swap that threw; both sentences are true and nothing is blank, so the
   order stays as landed and an order rule waits for a fault that shows itself; item 1's "first child" reads with this
   one exception. The claim that the Comments panel pairs over the fallback rows was held by source pins alone until
   the manager's round 1, which added the executed case to the failures leg (its seventh scene, on the pane: a note
   whose Rendered paint throws at the open, a comment stored beside the file beforehand pairing over the fallback Raw
   rows with one highlight inside a row and none elsewhere, no error row and no loader in the aside, the failure line
   the body's first child, `mode()` raw and `error()` null, the Rendered button pressed; then the healed Rendered
   click rendering the note and the pass painting the highlight inside `.fileview-md` with none left in a row, no page
   error; green over a git archive of 98859d061, as a case for shipped behaviour is, and red under a `contentRoot`
   that reads `.fileview-md` whatever `mode()` says, which paints nothing over the rows).
7. *Item 7, the CR rows.* One module-level regex in file-view.ts, `RAW_ROW_SPLIT = /\r\n|\r|\n/` (CRLF first, so it is
   one ending; then a lone CR; then LF), used by `wrapNumberedHtml` over the highlighted HTML and by `codeBlock`'s
   gutter count, the one trailing empty piece popped as before, so the two stay in step and no row's text carries a
   "\r"; the span-balance walk per row is unchanged, so an hljs span across a CR is closed at the row's end and
   re-opened on the next row as across an LF (hljs escapes markup characters alone, so a CR passes through its
   output). `scrollToOffset` reads the row through anchor-map's `rawRowForOffset(code, src, n)`, its signature
   unchanged, the verified row map that follows whatever split the rows were built on, an offset past the end landing
   on the last row as before, and when the map refuses (rows that do not match the source, which only a bug produces)
   counts the row over the source with the same split, clamped to the last row, exact by construction and never a
   silent last row; the second line counter is gone (open question 15, the default). `rawOffsetToLine` (anchor-map.ts,
   C4c) counts all three endings, a CRLF as one; an offset on an ending's own character still lies on the row the
   ending closes, as the verified row map places it, so the two agree row for row, and the panel's `landOn` keeps
   calling it, so the landing cue lands on the right row of a CR-only file. The editor's refusal over pending changes
   (`trackedRefusal`) keys on ANY "\r" and its sentence is the exported `CR_REFUSAL` ("The editor rewrites this file's
   CR or CRLF line endings as it loads the text, and that would move the pending changes."), shown with the panel's
   own refusal after it, the closure const `CRLF_REFUSAL` gone (open question 14, the default; verified before
   widening against the vendored editor, whose state package splits a string document on CRLF, a lone CR or LF alike
   and joins its lines back with LF, the chunk setting no line separator, so a lone CR is a line break on load and
   comes back LF exactly as a CRLF does through `norm`). One difference recorded in the constant's doc: a CRLF loses a
   character per ending, so offsets after it move; a lone CR keeps its offset but becomes another character, so a
   record whose text crosses one no longer matches, and the save wrote LF where the file had CR under records anchored
   to the disk bytes (the save door writes the CR back since the manager's round 1, below); the refusal is right for
   both. Before the slice `codeBlock` split the text on "\n" alone and set the rows through innerHTML, so the HTML
   parser turned a CR-only file's CRs into breaks inside a single row numbered 1, a CRLF file's rows each ended in a
   "\r" the parser rewrote, `scrollToOffset` kept a second line counter over LF alone so every offset in a CR-only
   file landed on row 0, `rawOffsetToLine` counted LF alone so a Reveal cued the first row while the viewer centred
   another, and the refusal keyed on CRLF alone, so a CR-only file's pending changes went into an editor that rewrote
   every ending under them. The departure from the plan's text: the refusal is widened from CRLF to CR or CRLF (the
   guide's sentence follows). Consumers that follow the split with no change: `rawRowSpan`, `rawRows`, the reader's
   Raw read, `scrollToLine` (by row index), `linkifyFileText`'s line units, `normalizeSource` (the Rendered pairing's
   own CR map). One consumer the build missed, found by the review's round 1: `lineStartOffset`
   (file-comments-model.ts), the counter behind the composer's Switch to Raw offer, inverted `rawOffsetToLine`'s row
   while counting LF alone, so on a CR-only file the offer scrolled to the file's end (`source.length`, its
   past-the-last-row answer) with the refused block out of view; it walks the three endings now, written locally since
   the module takes no anchor-map import (file-comments-model-line-start.test.ts, new: LF, CRLF, CR-only and mixed
   rows, the Switch to Raw scene over a synthetic note joined with each ending, and a seeded fuzz holding it to an
   independent split and to `rawOffsetToLine` at every offset; in headless Chromium the CR-only note's Switch to Raw
   centres row 53, the block's row, as the LF and CRLF copies do, where it centred row 79 of 83 before).
   `rawOffsetToLine` itself counts with two native searches since the same round, every LF before the offset and then
   every lone CR before it, in place of the build's per-character walk, which took about twenty times the pre-Slice 7
   LF-only loop at the end of a 2 MB text, once per Reveal title on every render of the Comments panel; the row
   answered at every offset is unchanged (anchor-map-raw-offset-to-line.test.ts, new: a same-run ratio against the
   LF-only count over fifty Reveal titles on a 2 MB LF and a 2 MB CRLF text, bound 6 where the build's body measured
   20, and seeded texts over the three endings answering the split's row at every offset). One consumer outside the
   viewer, found by the manager's round 1: the two save doors split an edit entry's lines on different sets, the
   kernel's `_edit_log_diff` on Python's `str.splitlines` (a CRLF as one ending, else a lone CR, LF, VT, FF, FS, GS,
   RS, NEL, LS or PS) and the host's `editDiff` on the engine's LF-only `splitLinesKeep`, so one edit on a CR-only or
   a form-feed-separated file read `@@ -1 +1 @@` over the whole text in the host's entry and `@@ -2 +2 @@` in the
   kernel's while the host's header claimed the kernel's shape; the host splits on the kernel's set now
   (`splitLinesKernel`, exported, the header naming the eleven endings as the one rule for both doors), and one
   fixture holds both doors to one answer, tests/fixtures/file_comments/save-doors.json (`editDiffLineEndings`: an
   edit on a CR-only, a CRLF, a form-feed-separated text and one carrying the rest of the set, each with the diff the
   kernel's difflib writes and its `@@` lines), read by tools/file-comments-host-save.test.mjs (the eleven endings
   split with a CRLF as one and the tail without one, the fixture case by case, and the door end to end over a tracked
   CR-only file whose entry is the fixture's diff on the reply and on disk; red over a git archive of 98859d061 at the
   CR case's hunk numbers) and by tests/test_savefile.py (`EditLogDiffLineEndings`, two: each case the kernel's own
   answer, and a plain save of a CR-only file through `_save_file` and `_edit_log_after` carrying it). Before this the
   divergence showed on a form feed or a U+2028 inside a line rather than on a CR-only save (the editor's refusal
   above holds a CR-only file's pending changes out of the editor, and the vendored editor joins a plain Save's lines
   with LF); the rule now holds for whatever text reaches either door. A consequence of this item's default, recorded
   in the review's round 1: a `path:N` link from an LF-counting tool (grep -n, a compiler, a traceback) lands on the
   viewer's row N, above the tool's line N when lone CRs stand inside LF lines, where main's LF-only rows landed on
   the tool's line; editors count a lone CR as a break too, and the producers disagree among themselves.
   file-view.test.ts (the `wrapNumberedHtml` replica splitting on the regex, with a CR case, a CRLF case with no
   phantom trailing row, a mixed case, two empty CR-ended lines, no CR or LF in any row's markup and a string span
   across a CR rebalanced, the template pin unchanged; source pins over `RAW_ROW_SPLIT` and both split lines with no
   LF-only split left between them; a source pin over `scrollToOffset`'s closure, the guards, the map first, the
   fallback count with the same split, the LF counter gone, the separate import line, one call),
   file-view-seam.test.ts (`layRows` splitting as the viewer does; the `scrollToOffset` case re-aimed and widened: an
   LF file with row 3 centred and past the end the last row, a CR-only file reloaded under the Raw view with row 3
   where the LF count gave row 0, the sixth line's row and past the end the last row, a CRLF file's sixth line, and
   the map refusing over rows laid with the wrong text with the count over the source giving row 3 and clamping past
   the end; the CRLF wording pin re-aimed to the widened sentence and the exported constant),
   file-view-tracked-edit.test.ts (13, three new over a CR-only document: pending changes known at the click refused
   in the widened words before the consent read, where the base sent the consent read; pending changes landing during
   the consent read refused at the mount, where the base mounted; without pending changes Edit mounting, the third
   case widened in the manager's round 1 to the save round trip, below, where the build had the chunk receive the text
   with its CRs intact and recorded the rewrite as the editor's own; the source pin re-aimed to `/\r/` and the
   exported constant with `CRLF_REFUSAL` gone), file-view-raw-rows-browser.test.ts (2 legs, new, over the real viewer
   with `raw: true`, pane and feed: "a\rb\rc\r" giving three `.fv-cl` rows with texts a, b, c, no CR or LF in any row,
   each row's `::before` with the computed content `counter(fvln)` and the counter increment and the pre's counter
   reset, the digits 1, 2, 3 read off Chromium's accessibility tree through the DevTools protocol, since every engine
   answers the computed `content` of a counter unresolved and the digits cannot be read through getComputedStyle as
   the brief supposed, the map verifying three rows and answering the third for offset 4, `scrollToOffset(4)` leaving
   the third row's box within the body's, a CRLF file giving three rows and no phantom row, a mixed file four; a
   two-hundred-line CR-only file giving two hundred rows with `scrollToOffset` on the hundred-and-fiftieth line's
   offset scrolling that row into the body and the first rows above it, the digits 1, 150 and 200 on their rows; no
   page errors), anchor-map.test.ts (C4c's case: the `rawOffsetToLine` case's lone-CR assertion flipped, offset 2 of
   "x\ry" being row 1; one case over a CR-only, a CRLF, a mixed and a blank-rows source laid on the three-ending
   split, `rawRows` verifying rows carrying no ending, `rawOffsetToLine` answering the split's row at every offset and
   agreeing with `rawRowForOffset` row for row, unclamped past a trailing ending as before, a selection across the
   first ending quoting the file's own endings, and item 6's control, zero rows over an empty source accepted with no
   error), file-comments-reveal-landing.test.ts (10, seven in the build and item 4's three BOM cases in the review's
   round 1; the stand-in's rows and its `scrollToOffset` following the three-ending split; one scene over the same
   document with every line ended by a lone CR: ten rows, Reveal on the deletion cueing line 6, the row holding the
   change and the row the viewer centred, Reveal on the substitution moving the cue to line 4). Three source pins in
   unit C's files read the lines A7 changed and were red from A7 until the consolidation pass re-aimed them to the
   contract's addenda: file-comments.test.ts and file-comments-reveal-landing.test.ts pinned the LF counter line
   `scrollToOffset` no longer holds and now pin `rawRowForOffset(code, src, n)`, the fallback's count over the source
   with `RAW_ROW_SPLIT` clamped to the last row, and no LF-only count; anchor-map.test.ts pinned `const lines =
   html.split("\n");` in `wrapNumberedHtml` and now pins the module-level `RAW_ROW_SPLIT` and
   `html.split(RAW_ROW_SPLIT)`. The suite's own replica of that function now splits on the three endings and builds
   the three-ending cases (C4c's local builder folded into it); the brief's premise that the older Raw grid cases hold
   either way did not (nine went red: their offsets, row counts and quotes were written over the LF-only grid, where a
   CRLF row carried a "\r" and a lone CR stayed inside its row), so those cases keep that grid as the map's input
   through a builder named for it, `wrapNumberedHtmlLf`, with a comment saying why; the map takes whatever rows it is
   given and verifies them against the source. The counts above are unchanged by the re-aim. Recorded by the build and
   fixed in the manager's round 1 under the manager's ruling that a save which rewrites line endings unasked changes
   data the reader never touched: without pending changes a save of a CR-only file wrote LF where the file had CR
   (`norm` rewrote CRLF alone, the editor's document model rewrites a lone CR on load, and the buffer was written as
   it is) once a keystroke had made the buffer dirty (`dirty` follows `onChange`, `docChanged` alone, and `doSave`
   exits without writing when nothing is dirty; the review's round 1 corrected this note's earlier clause that Save
   was offered before any keystroke), a pre-existing edge identical on main, the alternative of open question 14. Now
   `norm` reads a lone CR as the editor's document model does (`s.replace(/\r\n?/g, "\n")`, CRLF or CR to LF), so the
   dirty compare and the post-ack in-flight compare read the buffer against the editor's own view and an untouched
   buffer is clean, after a keystroke and its undo too; `eolCR` is set at the editor's entry when every ending is a
   lone CR (`/\r/.test(text) && !/\n/.test(text)`, exact by construction since the file has no LF of its own), and
   `doSave` writes the lone CRs back where the buffer has LF, the CRLF restore's shape (`eolCRLF ? ... : eolCR ?
   buf.replace(/\n/g, "\r") : buf`), so a typed change lands with every ending a CR; a file mixing CR and LF has no
   one ending to restore and saves as the editor gives it; `CR_REFUSAL`'s doc and `trackedRefusal`'s comment say so,
   the refusal over pending changes unchanged, and no kernel or host change was needed
   (file-view-tracked-edit.test.ts's third CR case, widened: the chunk receiving the LF view, a buffer equal to it
   posting no save verb and no saveFile frame and leaving edit mode, a typed change through the panel's save posting
   the CR document plus a line ending in CR, the ack leaving edit mode; editor-lazy.test.ts (16) pins the content
   line, `norm` and the `eolCR` assignment, its executed replica adding the CR round trip, a typed line break taking
   the file's ending and the mixed-file edge; red over a git archive of 98859d061 at the buffer holding the CR text
   and at the content pin; the guide's Edit paragraph says a file without pending changes keeps its CR or CRLF
   endings). Recorded, not changed, except where a clause says the manager's round 1 changed it (the hljs edge and the
   fallback count accepted as recorded there): `trackedRefusal` keys on `/\r/` over the whole text, so a stray CR
   inside a line refuses too, accurate to the editor's behaviour though the sentence says "line endings"; hljs's
   grammars key line starts on LF, so highlighting inside a CR-only file may be coarser than on the same LF file,
   cosmetic; the fallback count at an offset pointing AT the LF of a CRLF answers the row after where
   `rawRowForOffset` and `rawOffsetToLine` place it on the row the ending closes, reached only when the map refuses (a
   bug) and harmless, a count of endings whose last character lies before the offset being the exact form if wanted;
   `RAW_ROW_SPLIT` was declared below the closure that uses it, fine at run time and typecheck, until the manager's
   round 1 moved it with its comment up among the module's constants after `CR_REFUSAL`, above `openFileView`, whose
   `scrollToOffset` fallback reads it (file-view.test.ts asserts the declaration precedes the closure and reads the
   Raw view's slice from the builders; anchor-map.test.ts's and the line-endings suite's pins read the line
   position-free); `fencedRanges` (file-comments.ts) splits the source on "\n" for embeds, a pre-existing CR edge
   outside this item; `paragraphAt` and `changeGroups` (file-comments-model.ts) did too until the manager's round 1,
   so on a CR-only file the Comments panel's pending changes fell into one group titled by the document's first sixty
   characters flattened and a blank line's "line N" title counted no row, where the LF and CRLF copies of the same
   note grouped by paragraph, the marks painting on the right rows; the LF-only code is pre-existing and identical on
   main, but the disagreement with the Reveal title, the landing cue and the Raw rows is this slice's, since this item
   taught those three to count every ending (the review's round 1 routed it as pre-existing; the manager's round 1
   corrected that reading and ruled the fix), and both readers now take the module's `LINE_ENDING`, the three-ending
   rule `lineStartOffset` reads too and the viewer's `RAW_ROW_SPLIT` states, so a paragraph on a CRLF file ends before
   its CRLF rather than between its CR and its LF (file-comments-model-line-endings.test.ts (6, new in the manager's
   round 1): the CR copy of the notes-api note giving the LF copy's paragraph at every offset and its groups' four
   titles, members and bounds with a blank-line deletion titled "line 2", `rawOffsetToLine` plus one; the CRLF copy's
   bounds shifted by the endings before them, a paragraph ending before its CRLF, the blank row empty; an offset on an
   ending's own character, the LF of a CRLF included, lying on the row it closes; a fuzz of four hundred texts over
   letters, space, LF, CR and CRLF from a fixed random sequence, every offset against an independent row oracle, each
   blank paragraph's title `rawOffsetToLine` plus one and `lineStartOffset` inverting it; and source pins on the
   constant, the viewer's regex, no LF-only search left and the three reads of the rule; 0 of 6 over a git archive of
   98859d061, 6 of 6 at the fix); the gutter and the rows stay in step except when hljs closes a span after the file's
   final ending, where the trailing piece holds closing spans alone and survives the pop, so the Raw view shows one
   empty numbered row more than the file has lines, a `{ line: n+1 }` target lands on it without the past-the-end
   notice and a `{ line: n+2 }` target's notice counts the phantom row, pre-existing with LF endings on main and
   reached with CR and CRLF endings too since the split; the reach is not one construct (the review's round 2
   corrected this clause, which had named the markdown grammar's indented code block at a file's end alone): any mode
   the grammar leaves open at the file's end does it, an emphasis opened at an unpaired `_` or `*` outside code
   anywhere in the file (one subscript in inline math, `$o_2$`, or one snake_case word is enough; two pair and close
   it), an inline tag left open, an unterminated fence, and the indented code block at a file's end, while a display
   formula shows it only when its content leaves such an emphasis open, and a paragraph, heading, rule, quote, figure,
   list or closed fence ending the file shows none of its own; in headless Chromium over the branch 275 of 600 seeded
   synthetic notes opened in Raw showed the row, and of the 336 LF notes among them the same 169 showed it on main
   462ad3ccf (a pop of a trailing piece holding closing spans alone is the fix, routed); two chip suites' `rawRows`
   helpers split on "\n" and pin the template line alone over LF-only fixtures, exact for them, a one-line re-aim if
   wanted.
8. *Item 8, the records.* docs/guide.md, four paragraphs of the Files section in the build, each by appended lines
   with every existing line byte-identical except the two of the CRLF sentence the slice widens, and three of them
   again in the manager's round 1 (four sentences, below), drafted with the jld skill: "How a markdown file reads"
   says a file that cannot be shown as rendered Markdown shows its text as written, the way Raw shows it, under a line
   that says so and names the error, Rendered staying chosen and the next reload or click of the button trying again;
   "Your place in the file" says an empty file says so in place of its text and Edit still opens it; "Figures" says a
   figure that cannot be loaded shows a line where the picture would be, Image failed to load, then the figure's path
   as written and its alt text; the Edit paragraph's line-ending sentence names CR or CRLF, and a new sentence says a
   file that is not UTF-8 on disk can be read but not edited, with a line above the text saying why, a save would
   rewrite its bytes as UTF-8. The hard-wrapped lines other pins read (the opening paragraph's folder lines) stand
   byte for byte, and the twenty-one earlier guide modules ran green one at a time. The panel's row for a reload that
   failed (`BYTES_FAILED`) got no guide sentence from the build, the brief's item 8 naming five, and its export was
   held as a record pin; the manager's round 1 ruled a sixth sentence in, since the guide describes what ships, and
   three more went in with it under the same reading: "Your place in the file" says, after the changed-on-disk
   sentence, that with the Comments panel open the panel itself reads the file again and a failed read puts a line at
   the top of its cards saying so (The file could not be read again) with the reason in parentheses and Reload, and,
   after the empty file's sentence, that a file whose only bytes are a byte order mark says so instead
   (`BOM_ONLY_FILE`, item 6); "Figures" says a picture opened as a file of its own whose bytes will not decode shows a
   line in its place (`DECODE_FAILED`, item 3), then the file's path and Download; and the Edit paragraph says, after
   the refusal, that without pending changes such a file can be edited and its all-CR or all-CRLF endings are saved as
   they were (item 7). tests/test_guide_files_failures.py (19, thirteen new in the build: the five sentences
   flattened, in their paragraphs, each at the paragraph's end after the sentence that closed it before the slice, the
   old CRLF sentence gone; the neighbouring clauses other pins read, the Outline and changed-on-disk sentences, the
   files-pane lines and the Edit paragraph's wraps before the widened sentence, re-read unchanged; and against the
   source, each constant's exact export line, the phrases each guide sentence shares with its constant's value read
   off the source so a wording change in either fails beside the other, and the line that shows each: the
   `RENDER_FELL` line's text and `mode()`'s closure, the figure label's text, the body's capture-phase error listener,
   the mark, both `CONTROL_CLASSES` lists and the sheets' rule head, the `EMPTY_FILE` line's two prepends and the Edit
   gate, the `notUtf8` header read and the raise before `landTarget`, `trackedRefusal`'s `/\r/` line with
   `CRLF_REFUSAL` gone, and the record pin on `BYTES_FAILED`; 0 of 13 over a `git archive` of e6aeb1138 and 7 of 13
   over the worktree before the guide edit, the constants on the branch and the sentences not; and six more in the
   manager's round 1: the four sentences in their places, each directly after the sentence it qualifies or closing its
   paragraph, the decode and BOM-only constants' export lines and the lines that show them, the panel's export, row
   and place at the top of the cards read against the guide's words as the five are, the save door's `norm`, `eolCR`
   and content lines, with the Latin-1 raise pin re-aimed to the guarded line and the empty-file prepends to the
   byte-count ternaries; 10 of 19 red over a git archive of 98859d061 with the round's module copied in, the four
   sentences and the two exports absent there), tests/test_guide_files_place_and_outline.py (14, unchanged; its
   Outline and changed-on-disk pins stand in the paragraphs this slice extends), tests/test_files_pane.py (24,
   unchanged; its raw folder lines stand). This note; tests/test_markdown_viewer_plan_note_counts.py (5, unchanged; it
   accepts this note, the list below naming every test file once with the count each item states) and
   tests/test_markdown_viewer_plan_note_history.py (10, unchanged; it reads the Slice 6 note alone, and this note
   makes no claim of that kind). The ledger entry is upstream/2026-09-14-markdown-viewer-slice7.md (tier feature, the
   brief's open question 21 at its default, matching PR 753 and six of the eight sibling entries; its `where:` line
   names every file the branch changes and says the kernel's `_save_file` and `_edit_log_after` need the live kernel's
   restart; `pr:` set once the PR exists), checked by `scripts/upstream-ledger.py check` and
   tests/test_upstream_ledger.py (83, unchanged). The code comments that stated the old boundary are reworded by the
   units that own them, in the commits that moved the boundary: `mdBlock`'s catch comment moved to the callers; the
   seam's `text()` and `onRendered` docs; the landing hold's comment (a throw from a parked run reaches renderBody's
   own catch first); the panel's "the seam reports no failed fetch" and the deadline's reason (an older kernel alone);
   the unmapped hunks' comment; anchor-map.ts's split comment and `rawOffsetToLine`'s doc; the host's text contract
   restated with the save's re-prepend; `_save_file`'s docstring with the BOM rule; the headers of the place-memory
   and outline suites on the fallback parse they no longer need. CONTEXT.md is unchanged: the build coined no term
   (open question 22 covers this note's shape: the tests-by-file lead with the twenty-and-ten thresholds met, the
   pre-rebase shas mapped in the head's one sentence, no per-file identity claim and no new history module; the Slice
   6 note's head untouched). What the earlier slices routed here, each with its verdict: (a) the Slice 6 note's
   routing sentence, "Slice 7's failure paths, the VS Code host and the raw HTML `<table>` stay where they were": the
   failure paths are this slice's items 1 to 7, and the one thing inherited from Slice 6's reload work is that the
   failed Reload's re-arm runs AFTER the failure pane's paint, so item 3's hook call sits between the paint and the
   re-arm; the VS Code host's dead `line` arm and the raw HTML `<table>` are not this slice's, recorded, nothing
   built. (b) The math source fallback's title-only reason (the Slice 1 record: `showSource` shows the TeX as
   `code.md-math-src` with the reason on its `title`, every KaTeX failure routed there): not changed, the owner's call
   between the merged title convention and a visible reason for every dotted-underline failure at once, and the
   `cursor: help` nit on `code.md-math-src` in both sheets not taken (open question 18, the default); the formula's
   text IS shown, so the acceptance's "never a blank or bare glyph" holds already. (c) The edges the Slice 6 note and
   PR body recorded, each with its scope verdict as the brief gave it: the fetch-failure pane takes no keyboard, out
   of scope, since the disk bar's re-arm reads whether anything holds the keyboard AFTER the pane's paint and a take
   on either side of it would defeat that rule (open question 19); a deleted file's HEAD read as a move, "loose words
   for a deletion under the one-bar rule", out of scope for the wording, while item 3 makes the pane a paint the panel
   hears (open question 20); whether the changed-on-disk bar should outrank other notices, out of scope, item 5 saying
   which wins when both are due (the bar, raised later, takes the row; the line returns at the Reload's landing after
   `settleDiskBar`); a heading target under a plain `hidden` wrapper, whose notice the Slice 6 PR review wrote, out of
   scope here; the Rendered offset landing over a source with no blocks, in scope under item 6 for the empty file
   alone; the HEAD probe's network failure painting nothing, out of scope by the Slice 6 brief's ruling; a `file://`
   URI with a section on its tail inside a shown file's text, out of scope, the failure surface right and the defect
   the link grammar's; `readAt` refusing a fractional line silently, out of scope, the producers writing integers; and
   the remembered place writing no record without a text view, not a defect, item 1 stating and pinning its own
   consequence, that the fallback rows ARE a text view and a leave from them writes a Raw record while the failure
   pane still writes none. (d) Not in this slice's theme and left where they are: the caret-to-offset export, the
   Slice 6 note's focus items, the place memory's cross-kernel key, the anchor-map follow-ups of Slices 5 and 8, the
   PDF viewer and the other parser; the PDF frame's own failures stay the browser's, as the guide says. The brief's
   open questions, each taken as recorded above: 1 the stacked base, the call of the session that directed the build;
   2 the line in the body; 3 one try per viewer around build and swap; 4 the button pressed and `mode()` raw; 5 every
   failure path fires, a first open's too; 6 a required `error()` with closure state and the stub sweep; 7 the `<img>`
   element; 8 the img kept, the label its sibling; 9 the fact, the src and the alt, no reason; 10 the landed shape,
   the host's text kept and the plan's clause read as the offsets agreeing; 11 both doors on their own disk read; 12
   the editor mapping the seed and the host mapping back; 13 the raise before `landTarget` and the re-raise after
   `settleDiskBar`; 14 the refusal over any CR with the LF rewrite recorded; 15 `rawRowForOffset` with the exact
   fallback count; 16 the line above the empty root, not the bar; 17 the node-only sanitizer seam with the audit; 18
   the math fallback unchanged; 19 the pane's keyboard out of scope; 20 the two wordings out of scope; 21 tier
   feature; 22 this note's shape. The costs the units measured: item 2 adds two capture-phase listeners per open (the
   body already had one for `load`) and one CSS rule with one print line; item 7 changes one regex and reads the
   verified map in `scrollToOffset`; item 1 adds a try per viewer; item 3 a string, a required member and one hook
   call per failure pane; item 5 a header read and one notice; item 6 a prepend; nothing runs per frame, and no other
   measurement is owed. Two test-only facts the build recorded: editor-lazy's chunk test was red under the single-file
   recipe and green in the full suite, which the build read as two copies of the editor's state package in the linked
   node_modules; the manager's round 1 ran the file under the recipe and found two causes, the chunk test reading the
   metafile key of one copy resolved through the linked node_modules (esbuild realpaths the alias through the symlink,
   so the key is a relative path into the real tree, the test over-specifying the key; it reads the key's tail since,
   one input per package ending node_modules/@codemirror/<pkg>/dist/index.js) and the executed track test needing
   testBuild's CodeMirror alias, without which a plain `esbuild --bundle` puts two copies of @codemirror/state in the
   test bundle itself (the recipe, recorded in the file's header: NODE_PATH and the two --alias flags), 16 of 16 green
   over a git archive of 98859d061 under that recipe and at the fix; and the known box-only failure on plain main
   stands (file-comments-regions-layout-browser's first leg, font metrics, green in CI), reported and never loosened.
   Tests, by file (every new node test on the shim's stand-ins with `hideEdges`; every browser leg over headless
   Chromium and the real bundles, 0 skipped, counted on every run): file-view-seam (58, ten new in the build, three in
   the review's round 1, three in its round 2, two in its round 3 with one pin re-aimed and one added, one in the
   manager's round 1 with two cases re-aimed), file-view (59, four new in the build, one in the review's round 1, one
   in its round 2, eight pins re-aimed in its round 2, five re-aimed and four added in its round 3, pins re-aimed and
   added in the manager's round 1), file-view-links (28, re-pinned, one pin re-aimed in the manager's round 1),
   file-view-place (8, re-pinned, two pins re-aimed in the review's round 2, one in its round 3, pins re-aimed in the
   manager's round 1), file-view-place-memory (13, the stand-in installed), file-view-outline (15, the stand-in
   installed, two cases re-aimed, one pin re-aimed in the manager's round 1), file-view-text-size (33, the stand-in
   installed, one pin re-aimed in the review's round 4), file-view-tracked-edit (13, three new, one widened in the
   manager's round 1), editor-lazy (16, pins and its executed replica extended in the manager's round 1, the chunk
   test reading the metafile key's tail and the header recording the single-file recipe), file-view-edit-events (6,
   the stand-in installed), file-view-edit-races (10, the stand-in installed), file-view-undo-landed (11, the stand-in
   installed), file-view-undo-landed-ack (5, the stand-in installed), file-view-pdf-chunk-latch (5, the stand-in
   installed), file-view-pdf-frame (12, the stand-in installed), file-view-pdf-lifecycle (10, the stand-in installed),
   file-view-reload (23, five scenes extended, one new in the review's round 2), file-comments-save-busy-viewer (3,
   the stand-in installed and the stub line), md-url-view (29, re-pinned, one pin added and one re-aimed in the
   review's round 1, one re-aimed in its round 2), md-sanitize (19, one new, the seam pin sweeping the production
   sources since the review's round 1, its stand-in through `hideEdges` since the manager's round 1),
   file-view-landing-throw-browser (2 legs, re-aimed), file-view-failures-browser (7 legs, new: four in the build, one
   in the review's round 1, two in the manager's round 1 with the Latin-1 scene extended), file-view-figure-error (10,
   new: seven in the build, two in the review's round 1, one in the closing pass; the formula pin re-aimed in its
   round 2), file-view-figure-empty-source (1, new in the review's round 2), file-view-figure-error-browser (3 legs,
   new: two in the build, one in the review's round 1), file-view-raw-rows-browser (2 legs, new),
   file-view-fell-wrap-browser (1 leg, new in the review's round 4), fileview-parity (4, one head; the `.fileview-err
   {` head added in the review's round 4), anchor-map (43, three new in the build, two in the review's round 1),
   anchor-map-raw-offset-to-line (2, new in the review's round 1), anchor-map-cells-browser (6 legs, one read
   re-aimed), render-sanitize (3, one pin re-aimed), anchor-map-fallback-markup (25, the mirror list),
   md-config-figure-gate-place (1, two scenes), file-comments (35, re-pinned, one pin re-aimed in the review's round
   2, two in its round 3), file-comments-changes-review2 (23, one scene in the build, two in the review's round 1,
   four in its round 2, two in its round 4 with three re-aimed), file-comments-changes (23, one pin re-aimed in the
   review's round 1), file-comments-editing-round3 (7, one pin re-aimed in the review's round 1),
   file-comments-changes-review (12, one case flipped), file-comments-about-fixes (8, one case flipped),
   file-comments-editing-races (14, one new), file-comments-reveal-landing (10, one new in the build, three in the
   review's round 1, one pin re-aimed in its round 2), file-comments-reveal-title (6, one new in the review's round
   1), file-comments-model-line-start (6, new in the review's round 1), file-comments-model-line-endings (6, new in
   the manager's round 1), file-comments-behavior (22, one pin re-aimed in the review's round 2, one in its round 4),
   file-comments-editing-moved-latch (4, one pin re-aimed in the review's round 4), styles-fileview-err-sizes (7, one
   pin widened in the review's round 2), the 118 stub files of the sweep with one line each and no count moved (five
   of them counted above: file-comments-changes, file-comments-editing-round3 and file-comments-reveal-title since the
   review's round 1, file-comments-behavior since its round 2, file-comments-editing-moved-latch since its round 4),
   the infrastructure real-viewer-leg.ts (`serve`, `before`, `waitFor`, the per-path header table, the map's exports,
   the page stub's Content-Length since the manager's round 1) and md-sanitize.ts's seam;
   tools/file-comments-host-save.test.mjs (19, five new: three in the build, two in the manager's round 1),
   tools/file-comments-host-tiebreak-review.test.mjs (12, one scene rewritten in the manager's round 1),
   tools/file-comments-host-untouched.test.mjs (9, one re-aimed), tools/file-review-plan-anchors-states.test.mjs (5,
   one pin re-aimed in the review's round 4); tests/test_savefile.py (26, eight new: six in the build, two in the
   manager's round 1, its BOM class over the shared fixture since then), tests/test_kernel_file_comments_save.py (24,
   two new), tests/test_kernel_file_comments_hardening.py (31, one re-aimed), tests/test_kernel_preview.py (31, two
   record pins), tests/test_file_view.py (22, one record pin), tests/test_guide_files_failures.py (19, new, the
   label's text pin re-aimed in the review's round 1, the catch's and the label's pins in its round 2, the Latin-1
   raise count in its round 3 with the pick's gate pinned beside it, six more in the manager's round 1 with three pins
   re-aimed), tests/test_guide_files_place_and_outline.py (14, unchanged), tests/test_files_pane.py (24, unchanged),
   tests/test_markdown_viewer_plan_note_counts.py (5, unchanged; it accepts this note),
   tests/test_markdown_viewer_plan_note_history.py (10, unchanged), tests/test_markdown_viewer_plan_note_slice7.py (5,
   new in the review's round 3: this note held to four of its own rules; its stage rule reading a round 3 count since
   its round 4), tests/test_upstream_ledger.py (83, unchanged). Every case that changes behaviour fails over a `git
   archive` of e6aeb1138 (the head the branch was cut from, with the new exports stubbed where a test imports one, and
   the readers' files beside ui, vendor, esbuild.js and package.json where a suite reads them) and, from the second
   commit of a unit on, over a `git archive` of the branch's head before the commit as a control that isolates the
   commit's own red, and says how and over which tree in its commit; a pin over a shape this slice moved is titled a
   re-pin and is red by construction over those trees; the record pins say they are records. The guarantees the
   families re-verify: highlights are measured `<mark class="fc-hl">` elements over the range's text nodes, and the
   paragraph holding a failed figure paints one under both sheets; the panel's boxes keep the keyboard through every
   paint, the failure pane's included, since the hooks fire before the disk bar's re-arm; the poll asks one reload per
   mtime and the save fence compares mtime strings, the BOM rule running on the read that fence guards; the pairing,
   the change marks and the selection map read the one block table, which item 4 maps by exactly `s.bom ? 1 : 0` at
   the paint and the seed and never rewrites, and which item 2's label never enters, being a control to both walks;
   item 7's rows keep every character of the line, the separator alone consumed, so `rawIndex` still verifies
   character by character and `scrollToOffset`, `rawOffsetToLine` and the rows agree on a CR file; and the composer's
   quote stays the exact source slice.

**Review round 1** (2026-09-14). The review of the branch at 103a13f32 over main 462ad3ccf, the first round after the
rebase, under the owner's efficiency plan: the whole branch read by a reader new to it, every finding checked by one
second reader for a low and by two for a medium or a high before it was acted on, the fixes made one hand per file,
and one consolidation commit ("Slice 7: review round 1 fixes"). The rule the round judged by: a Slice 7 edge is fixed
when it is a defect against a contract or the failure-says-what-happened principle, a regression against main, or the
feature's own gap that one exact change closes with a test red over a `git archive` of 103a13f32; a decided default is
recorded and not re-fixed; a pre-existing edge identical on main is recorded here and routed. The fixes, each recorded
in its item above: item 1's heading target and URL fragment waiting for the Rendered retry over a fallen render, and
the offset spender reading `mode()`; item 2's label naming the candidate the browser asked for, a `data:` source cut
to its head, and the label outside a link holding the figure alone; item 3's landing clause over a content paint
alone, and `bytesPaneGone`; item 4's three remaining panel reads of the host's offsets mapped by `bom` (Reveal's
scroll and cue, the card's line suffix, the change groups), a wrong row on a BOM file being HIGH by the owner's rule,
so the one dissenting reading, that the edge was pre-existing and should be recorded and routed, was overruled: the
slice's own mapping of the paint pass had made the mark and the Reveal disagree; item 5's `dropLatin1Line`; item 7's
`lineStartOffset` over the three endings, `rawOffsetToLine`'s two native searches, and anchor-map.test.ts's two cases
over the viewer's grid. The records. This note's head said the rebase had not happened and that the mapping would be
recorded at it, named E2 and E3 by their pre-rebase shas, and counted file-view-reload.test.ts,
file-view-outline.test.ts and tests/test_kernel_preview.py at 20, 14 and 27, the cut point's numbers plus the slice's
own, where main's two commits between the cut point and the base had added cases (the Slice 6 note counts the same
files at 22, 15 and 29, so the later note read lower than the earlier for files it only extended); the head now names
the base, maps all twenty shas, says what changed in the two patches that did not replay as written and which nine of
the slice's files those commits touched, and the mentions read 22, 15 and 31
(tests/test_markdown_viewer_plan_note_counts.py holds an item's count to the list's, not to the file's, by design,
since a later slice's additions leave an earlier note as written, so it accepted the stale numbers as it accepts the
corrected ones; no new module, the head's sentences are the record). The ledger entry's `where:` line said this note
mapped the pre-rebase shas when it did not; its opening clause records the rebase, the nine files and the range-diff's
two re-resolved pairs, and its file clauses name this round's changes. The landing hold's comment above `fetchFile`
described a path item 1 closed; it says now that a throw from the block's build or the swap is caught inside
renderBody's own try, parked or immediate, and only a throw from the fallback or the passes after the try rejects into
the chain's catch. md-sanitize.test.ts's seam pin said no production caller sets a sanitizer and asserted nothing
about the other modules; it sweeps the non-test ui/webview sources for `setMdSanitizer` and holds the list to
md-sanitize.ts alone, with `installedSanitizer` pinned module-private (red over the base with a stand-in module wired
into files.ts; the count stays 19). The D2 commit's message (a58644912; cb9aca26d before the rebase, the same text)
describes the typecheck window inverted, the stubs as missing a member with the sweep to follow, where at that tree
the stubs already carried `error` (C0c, three commits before) and `FileViewActionCtx` lacked it until A3; C0c's, D3's
and A3's messages and this note state it the right way round, and the message stands, since the round's rules bar a
history rewrite (a reword before the PR opens is the owner's call). Two things the round confirmed as the build left
them: the pairing's exclusion of the top-level label (`isFigureLabel`) and the landing's clearing of the panel's row
drew no defect from the review beyond item 3's narrowing. Pre-existing, identical on main, routed (low, found by the
check for comments regressions): the host's `readFile` (tools/file-comments-host.mjs) and the track-comment CLI decode
a file that is not UTF-8 with a U+FFFD per invalid byte, while the kernel's `_decode_text` serves the viewer a latin-1
fallback, one character per byte, so on such a file the view's text and the host's differ at every non-ASCII byte (and
in length where a run of invalid bytes folds into one U+FFFD): a comment made from the view over such a passage is
refused `anchor-not-found`, a sidecar comment the CLI writes is placed in the view by its context alone and painted as
changed text, and ASCII passages are whole; neither decode changed by the slice, item 5's gate already refusing the
save that would rewrite such bytes; one decode rule for both sides is the follow-up, a design call, recorded in
readFile's header comment. Observed on the way, not a finding: the row's Reload over the earlier text loses its loader
when the status lands before the fetch (fcreload's `refresh(slot)` deletes the busy slot in its finally after
`applyStatus`'s `awaitBytes` re-added it), identical on main for the deadline row's Reload; a fetch that then fails
still files the row, one that never lands shows nothing at the deadline (ended in the review's round 4: `refresh`'s
end leaves the "bytes" mark to an armed wait, item 3). Left open for the review's later rounds: the failed-Reload 413
scene the brief's item 3 names for file-view-reload.test.ts, a test-only addition not taken this round, and the
`where:` line's length. Tests, by file, this round (every count the branch's, as this note's head says, so the three
files round 2 added to read round 2's numbers here too; the additions named are this round's): file-view-seam.test.ts
(58, three new), file-view.test.ts (59, one new), md-url-view.test.ts (29, one pin added and one re-aimed),
file-view-figure-error.test.ts (10, two new), file-view-figure-error-browser.test.ts (3 legs, one new),
file-view-failures-browser.test.ts (7 legs, one new), file-comments-reveal-landing.test.ts (10, three new),
file-comments-reveal-title.test.ts (6, one new), file-comments-changes.test.ts (23, one pin re-aimed),
file-comments-editing-round3.test.ts (7, one pin re-aimed), file-comments-changes-review2.test.ts (23, two new),
file-comments-model-line-start.test.ts (6, new), anchor-map-raw-offset-to-line.test.ts (2, new), anchor-map.test.ts
(43, two new), md-sanitize.test.ts (19, one pin widened), tests/test_guide_files_failures.py (19, one pin re-aimed);
every new case that changes behaviour red over a `git archive` of 103a13f32 at the assertion its file's report names
(the review's round 2 corrected this clause, which had claimed every new case: anchor-map.test.ts's two cases over the
viewer's grid are green there, the painters needing no change, and are held red by the three painter-local mutations
item 7 records; anchor-map-raw-offset-to-line.test.ts's seeded fuzz and file-comments-model-line-start.test.ts's LF
and CRLF cases are controls, green there by design; the round's commit message, 402f95d2d, carries the blanket
sentence and stands, a rewrite barred by the round's rules), every re-aimed pin red there by construction, the
typecheck clean after every edit, and the round's full runs (the full npm test, CI's tools step, the pytest modules)
recorded in the build report outside the repo.

**Review round 2** (2026-09-14). The review of the branch at 402f95d2d over main 462ad3ccf, under the same plan as
round 1 (the whole branch read by a reader new to it, every finding checked by one second reader for a low and by two
for a medium or a high, the fixes made one hand per file, one consolidation commit, "Slice 7: review round 2 fixes")
and the rule round 1 judged by. The records this note corrects, each in its place above and each checked by an
executed probe before the words were changed: item 2's clause on the label's source counted a URL document's
candidates among those left as written, where the URL viewer's label names the resolved absolute URL, the viewer
having rewritten every relative candidate and stamped nothing (the comment on the remote case in
file-view-figure-error.test.ts said the same and says the viewer's rule now); item 7's clause on the phantom Raw row
named the indented code block at a file's end as its one cause, where any mode hljs leaves open at the file's end
causes it, an unpaired `_` or `*` outside code the commonest, so the routed fix reaches a large share of ordinary
notes; the round 1 paragraph's fails-before sentence claimed every new case red over 103a13f32, where the two
anchor-map cases over the viewer's grid and three controls are green there by design, as item 7 and the build report
already said of them; the same paragraph counted md-url-view.test.ts as two pins re-aimed, and item 8's list as two
more, where round 1 added one pin (test 24, `landFragment`'s guard) and re-aimed one (test 29, `spendHeading`'s
shape), and both mentions say so; and the same paragraph described the round by the roles of those who ran it in four
places, where this file's other notes describe a round by its rule, its fixes and its routings, so it does now (the
round 1 commit's message keeps its own wording of the fails-before claim, a rewrite barred). No count in the
tests-by-file lists moved for these corrections. The fixes, each recorded in its item above and each with a case red
over a `git archive` of 402f95d2d: item 1's `renderFell` recorded after the fallback swap through `fellMessage`, which
cuts marked's appended report-this sentence, so a fallback throw from a click leaves the previous paint and its record
and `mode()` answers what the body shows (a Raw view whose Rendered click throws twice answers "rendered" over the
rows because the click writes `fmt.md` before the paint: identical on main, pre-existing, routed); item 2's
`FIGURE_NO_SOURCE` in the label's source place for a figure that names none; item 3's `syncFailedRow`, superseding
round 1's `bytesPaneGone`, the failure row read against every later paint: gone at a landing that moves the view's
mtime, the pane's current words under a pane, the deadline row's tail under a content paint, the editor's entry
included; item 5's `dropLatin1Line` at the fetch chain's catch; and the landing hold's comment above `fetchFile`,
which named the hooks among the passes whose throw rejects into the chain's catch, where `fireRendered` swallows a
hook's own throw (file-view.test.ts pins the list). Taken this round, the test-only addition round 1 left open:
file-view-reload.test.ts's failed-Reload 413 scene (item 3), green at 402f95d2d and red under the mutation that
removes the catch's `fireRendered()`. The D2 commit's message stands as the round 1 paragraph records it, a rewrite
barred. Pre-existing, identical on main, routed (low, found by the checks for figures and for comments regressions):
the regions layer wraps THE img in `span.fc-imgwrap` (file-comments-regions.ts, unchanged since 462ad3ccf), and for an
img inside a `<picture>` that takes the img out of the picture, so the browser, which applies a `<source>` only to an
img whose parent is the picture, re-runs its selection and shows the img's own src while the Comments panel is open,
then re-selects the picture's candidate at the close: with the source's candidate missing and the src present, item
2's label leaves at the open (the img's `load`) and returns at the close (a second `error`), and with both present the
panel toggles which image shows; the label follows the browser's events and its place is unaffected (`figureAnchor`
climbs both wrappers), while contract C2's addendum and `figureAnchor`'s header record the place alone, not the
candidate change. The follow-up is the layer's: wrap the `<picture>` element when the img's parent is one (a span
around the whole picture re-selects nothing, probed in Chromium), with anchor-map.ts's `tagNameOf` answering the
wrapped element's tag rather than IMG alone. Pre-existing, identical on main, routed (low): a deletion whose host
offset is the source's length on a file ending with a line ending (LF or CRLF, with or without a BOM) titles its card
"(line N+1)" (renderChangeCard's suffix, `rawOffsetToLine(src, from) + 1`) and its paragraph group "line N+1"
(`changeGroups`, file-comments-model.ts), while `paintRawPoint` puts the point on row N and `landOn` clamps the cue to
it, the Raw view having N rows; probed with a ten-line LF and a CRLF document and a deletion at the text's length:
title "(line 11)", group "line 11", the mark and the cue on the tenth row, the control on the final ending reading
"(line 10)"; identical on 462ad3ccf. The follow-up: the two callers clamp as `landOn` does (`Math.min` over the rows'
count; anchor-map.test.ts pins `rawOffsetToLine` unclamped and the callers clamping), one node case each in
file-comments-reveal-title.test.ts and file-comments-editing-round3.test.ts. Pre-existing, identical on main, routed
(low): in the margin layout with Show changes inline off, a pointer click on a Reveal button that the track's box cuts
(a pane 800 by 500: the button at y 379 to 404, the track 201 to 392) scrolls the track 12 px at the press; the
click's re-render clamps the track back to 0 with no `syncFrom`, `scrollToOffset` puts the body at 2082, and at the
frame the track's queued scroll event runs first: `mirrorScroll("track")` writes 0 onto the body and takes the body's
own event for the echo, so the cue paints on row 85 while rows 0 to 14 show; a synthetic `el.click()` and a pane where
the button is whole (800 by 700) land the row (`mirrorScroll` and `writeScroll` in file-comments.ts are unchanged by
the slice). The follow-up: the panel's own body write on a Reveal owns the lock (`syncFrom` set to "body" before
`scrollToOffset`, or a track event queued before the write dropped), with a browser scene at 800 by 500 through the
pointer. Observed on the way, not findings, left for the review's later rounds: `trackedEdit.begin()` reads
`seedOf(status)` without `textCurrent`, so Edit clicked while a reject's reload is out, or after it failed (the gate
reads the last landing's text and mtime, so the button is offered over the pane), seeds the post-reject records over
the pre-reject text, wrong passages where the texts differ, for one round trip normally and for as long as the pane
stands after a failed reload (a refusal, or a plain editor, when the text is not the status's is the shape to weigh);
and `askReload` asks one fetch per mtime (`reloadFor` is never cleared by a failure) while `awaitBytes` arms
regardless, so after a Raw click over the failure row a comment's or a reply's status at the same mtime takes the row,
shows the loader with nothing out, and the deadline row follows at 15 s, the pre-existing loader-then-deadline loop,
where over the pane the head's clause re-files the failure row at once. Still open: the `where:` line's length. Tests,
by file, this round: file-view-seam.test.ts (58, three new), file-view.test.ts (59, one new, eight pins re-aimed: six
to item 1's three-line catch, the stamp pin, both try-shape pins, the line's count pin and the two empty-file
adjacency pins, and two to item 5's drop in the fetch chain's catch, the drop's count pin and the catch-order pin,
with two pins added beside them, that no catch paints the line from the record and the drop's place in the catch; the
round's commit message counts three, the consolidation's own, and stands, a rewrite barred; the review's round 3
corrected this count, which the two mentions had given as three), file-view-figure-empty-source.test.ts (1, new),
file-view-figure-error.test.ts (10, one pin re-aimed), file-view-place.test.ts (8, two pins re-aimed),
file-view-reload.test.ts (23, one new), file-comments.test.ts (35, one pin re-aimed),
file-comments-changes-review2.test.ts (23, four new), file-comments-behavior.test.ts (22, one pin re-aimed),
file-comments-reveal-landing.test.ts (10, one pin re-aimed), md-url-view.test.ts (29, one pin re-aimed),
styles-fileview-err-sizes.test.ts (7, one pin widened, the pane's chain read with or without the Latin-1 drop between
the offer and the swap; the last three found by the round's first full npm test, source pins over the editing branch,
the URL viewer's catch and the pane's chain that no single-file run had covered), tests/test_guide_files_failures.py
(19, two pins re-aimed); every new case that changes behaviour red over a `git archive` of 402f95d2d at the assertion
its file's report names (the seam's three at "no notice bar over the pane", "mode() answers what the body shows" and
"the message alone: marked's sentence and URL cut"; the empty-source case at "the fact, the empty source named as
such, the alt"; the four changes-review2 scenes as item 3 lists them), the 413 scene a control there, every re-aimed
pin red there by construction and the widened pin green there, admitting both chains (the review's round 3 corrected
this clause, which had counted that pin among the re-aimed), the typecheck clean after every edit, and the round's
full runs (the full npm test, CI's tools step, the pytest modules) recorded in the build report outside the repo.

**Review round 3** (2026-09-14). The review of the branch at 75ad5d042 over main 462ad3ccf, under the same plan as
rounds 1 and 2 (the whole branch read again, every finding checked by one second reader for a low and by two for a
medium or a high, the fixes made one hand per file, one consolidation commit, "Slice 7: review round 3 fixes") and the
rule round 1 judged by. This note corrects six records, each in its place above and each checked by an executed probe
before the words were changed. The head's `git range-diff` command ended its right-hand range at the branch's head, a
moving reference that since round 1 lists the review's commits after the consolidation commit as unpaired; it ends at
103a13f32, the last commit the pre-rebase lineage pairs with. The head's count sentence, which says every count is the
branch's, gave file-view-reload.test.ts 22, the base's count, where round 2's 413 scene made it 23 on the branch, as
item 3 and both tests-by-file lists already said; it reads 23 and names the round that added the third. Item 1's
parenthetical counted two round 2 cases in file-view-seam.test.ts against the three the list counts (39 at the base,
ten in the build, three in round 1 and three in round 2, one of the three item 5's failed-reload drop), a sum one
short of the 55 it opened with; it reads three. The round 2 paragraph and item 8's list counted three pins re-aimed in
file-view.test.ts, the consolidation's own, where the round re-aimed eight (six to item 1's three-line catch, two to
item 5's drop in the fetch chain's catch) and added two; both mentions read eight, and the round 2 commit's message
keeps its count of three, a rewrite barred. The round 2 paragraph counted styles-fileview-err-sizes.test.ts's pin
among the re-aimed and its closing sentence claimed every re-aimed pin red over 402f95d2d, where that pin was widened,
an optional group admitting the pane's chain with or without the drop, so the suite at this head runs 7 of 7 green
over a `git archive` of that tree (executed); the paragraph and item 8's list say widened, and the pin stands, since
the chain must match with and without the drop. The round 1 paragraph's twin sentence, checked the same way
(402f95d2d's tests over a tree of 103a13f32: md-url-view.test.ts's test 29, file-comments-changes.test.ts's test 11,
file-comments-editing-round3.test.ts's test 7 and tests/test_guide_files_failures.py's label pin, each red), stands.
The round 2 paragraph described one routing by the review's two checks in a word this file's other notes do not use,
and the head described the build's organisation with the word the review's plan uses for its own; the routing names
the checks (figures, comments regressions) and the head names the session that directed the build. A new module,
tests/test_markdown_viewer_plan_note_slice7.py (5, new), reads this section and holds it to those four rules: no word
the review's plan uses for those who run a round (their nouns and the verb of the one who directs it; not seed, which
the editor's seed and the seeded fuzz use in their own sense, nor coordinate, the offsets' word); a count the head
gives beside the cut point's is the list's; a `git range-diff` command names four fixed shas, never HEAD; and a file's
count by stage (new in the build, in the review's round 1, in its round 2) in an item is the list's. Red over the plan
of 75ad5d042 at four of its five cases (the plural the earlier checks had missed; 22 against 23; HEAD; two against
three), the premise case green there; green at this head. No existing count in the tests-by-file lists moved for these
corrections; item 8's list gains the module. The fixes, each recorded in its item above and each with a case red over
a `git archive` of 75ad5d042: item 3's `viewError` cleared once the text paint's swap stands, after the try's close
and item 6's line and before the folds' restore, rather than before the pass, so a format click over a standing
failure pane whose render swap and fallback swap both throw (a bug, not a file) leaves `error()` answering the pane
the body still shows, where before it answered null over the pane and the Comments panel's next pass at the same mtime
would have read the view as showing the earlier text (the seam case: a 404 pane with `error()` its words, every body
swap made to throw, the Rendered click and then the Raw click each throwing with the pane standing, no hook fired, the
mtime unchanged, `error()` the words and `mode()` "rendered", then a healed click painting the note and clearing the
record; red at "error() still answers the pane's words"; the three clear sites unchanged in number, the pins on the
pass's shape re-aimed in file-view.test.ts, file-view-place.test.ts, file-comments.test.ts and the seam suite); and
item 5's `pickFormat`, the one helper behind the bar's Rendered and Raw clicks and the seam's `setMode`, raising the
Latin-1 line again when its paint put the last landing's text back over a failure pane, which closes the state round 2
recorded and routed (the seam case as item 5 lists it; red at "the line is back over the repainted text"; two raise
sites, pinned in file-view.test.ts and tests/test_guide_files_failures.py). Closed as recorded, no words added: the
regions layer's wrap of a `<picture>`'s img and the margin layout's scroll lock on a Reveal, both in the round 2
paragraph with their scenes and follow-ups, the code they name byte-identical to 462ad3ccf (file-comments-regions.ts,
region-geometry.ts, `mirrorScroll` and `writeScroll`) and the record checked true of it this round. Pre-existing,
identical on main, routed (low, found by the check for figures, hooks and the seam): `awaitBytes` (file-comments.ts,
unchanged since 462ad3ccf; every line the slice adds naming it is a comment) runs on every applied status whose file
mtime is not the view's and re-arms the 15 s deadline each time (`clearTimeout`, then a fresh `setTimeout`), while
`askReload` asks one fetch per mtime, so in the one case the deadline is kept for, a reload that neither lands nor
fails through the seam's `error()` (a kernel from before this slice, or a stalled network), a stream of statuses under
15 s apart (the poll's refresh on a sidecar, config or figure move, a peer's comment, the person's own comment or
reply, each landing through `applyStatus`) keeps the loader at the head of the cards up with nothing out, and the
deadline row never files until the statuses stop for 15 s; over a quiet poll both trees file the row at 15 s, and this
branch's `bytesLanded` takes it at a late landing where main leaves it. Probed in headless Chromium over the Files
bundle (the report's GET held, the file's mtime moved, the panel reopened; a noisy poll from the store and config
HEADs answering 404) and in a node scene through file-comments-changes-review2.test.ts's world (the held reload, mock
timers, a peer's comment moving the sidecar every 12.5 s): loader 1 and no row past 22 s in the browser and past 40 s
in node, on 75ad5d042 and on 462ad3ccf alike, the row filing 15.0 s after the last status with one fetch asked in all.
The follow-up: arm the deadline once per reload asked (with `reloadFor`, in `askReload`, so a status that asks no
second fetch re-arms nothing) or re-arm only when the status's file mtime is not the one the standing wait was armed
for, with a node scene in file-comments-changes-review2.test.ts (mock timers, the held reload, statuses 10 s apart at
one file mtime, the row due 15 s after the first) red on 75ad5d042. Pre-existing, identical on main, routed (low): the
`.fileview-err` dress has no wrapping rule for an unbroken token (only `.fileview-err-hint` carries `word-break:
break-all`), so a RENDER_FELL line whose message holds a long unbroken token (a quoted attribute value, a URL) widens
the body at phone width (a 120-character token in the 380 px chat modal: 453 px of horizontal overflow on the line and
the body, the rows under it wrapping as before), as the pane's own 404 for a long basename does on main 462ad3ccf by
the same mechanism (520 px, identical on both trees); a follow-up adds `overflow-wrap: anywhere` to the dress in both
sheets with the parity head, if wanted, a change that reaches the note bar, the empty-file line and the pane, which
wear the same dress. Left open from round 2: `trackedEdit.begin()` reading `seedOf(status)` without `textCurrent`, and
the `where:` line's length. The seam suite's count reads 58 in every mention of this note, this round's two cases and
the manager's round 1's case included, as the head's rule has it. Tests, by file, this round: file-view-seam.test.ts
(58, two new, one pin re-aimed and one added), file-view.test.ts (59, five pins re-aimed, four added),
file-view-place.test.ts (8, one pin re-aimed), file-comments.test.ts (35, two pins re-aimed),
tests/test_guide_files_failures.py (19, one pin re-aimed, one added), tests/test_markdown_viewer_plan_note_slice7.py
(5, new); every new case that changes behaviour red over a `git archive` of 75ad5d042 at the assertion its file's
report names (the seam's two above; the module's four over that tree's plan, its premise case green there by design),
every re-aimed pin red there by construction, the typecheck clean after every edit, and the round's full runs (the
full npm test, CI's tools step, the pytest modules) recorded in the build report outside the repo.

**Review round 4** (2026-09-14). The review of the branch at 9c4fceac5 over main 462ad3ccf, under the plan of rounds 1
to 3 (the branch read by the round's checks and the findings round 3's re-check left open read again, every finding
checked by one second reader for a low and by two for a medium or a high, the fixes made one hand per file, one
consolidation commit, "Slice 7: review round 4 fixes") and the rule round 1 judged by. One correction is to this
note's line breaks alone, the words unchanged: round 3's rewording of three sentences (the head's sha mapping, item
8's list of the brief's open questions and the round 2 paragraph's routing of the picture wrap) re-wrapped only the
lines it changed and left a short line inside each paragraph (28, 20 and 15 characters: "5e6728847, 1af2be2bd (D1)
is", "too; 6 a required" and "which applies a") between lines filled to the 118 columns the build notes wrap at, where
each had been a filled line at 75ad5d042; the round 2 paragraph had carried a fourth since that round (48 characters,
"tests-by-file lists moved for these corrections.", a sentence's end with the paragraph running on). Each paragraph is
re-filled from the short line to the first line that ends where the earlier text's did, every line at or under 118
columns, the section's text identical once its wraps are collapsed (the reading the record modules make), and
tests/test_markdown_viewer_plan_note_slice7.py, the counts module and the history module green after the edit. No pin
is added for the shape: the modules collapse the wraps before they read, so a rewrap changes nothing they check, and a
pin on line breaks would go red at the next rewrap of any sentence. The fixes, each recorded in its item above and
each with a case red over a `git archive` of 9c4fceac5: the dress edge round 3 routed is fixed under this round's
sharpened rule for it (one declaration, or the record stands): the `.fileview-err` rule carries `overflow-wrap:
anywhere` in both sheets, byte-equal, its head `.fileview-err {` added to fileview-parity.test.ts's RULES, so a
failure message's long unbroken token breaks inside the line's box; the declaration reaches every wearer of the dress
(the fetch chain's pane, the note bar, the empty-file line, the comments panel's error row, the pdf page's notes) and
changes a box's width only where a word is wider than the box, which none of them holds, and
file-view-failures-browser (7), file-view-notebar-browser (9), file-view-landing-throw-browser (2), pdf-chunk-browser
(1) and styles-fileview-err-sizes (7) are green after it; the new leg file-view-fell-wrap-browser.test.ts (1 leg, new)
makes the swap throw at the first paint (`Element.prototype.replaceChildren` patched through openViewer's `before`,
the wait on the line through `waitFor`) with a 120-character token as the message on the chat modal, the feed modal
and the Files pane at 380 by 600, and holds the line's and the body's scroll widths to their client widths and the
computed overflow-wrap to "anywhere": red over the archive (computed "normal"; the line and the body 470 px past their
boxes in the two modals and 449 px in the pane, whose body is the pane's full width) and green at the fix (0 on all
three; the line 90 to 125 px tall in the chat modal and the pane, 86 to 120 in the feed), the ordinary-words control
fitting on both trees; item 1's sentence on the dress says so. Item 3's `reloadOut` (the mechanism in item 3): the
bytes row's Reload over a standing pane re-filed the failure row off that pane as soon as the status ask landed, the
fetch still out, with no loader for the read in flight and no deadline row if it stalled (low); `reloadView()` is now
the one door for every re-fetch the panel asks and sets the record, the viewer's next paint other than a reflow clears
it, the head's clause stands down while it is set, and `refresh(slot)`'s end leaves the "bytes" mark to an armed wait;
file-comments-changes-review2.test.ts (23, two new, three re-aimed) is red over the archive at five assertions naming
"before round 4" (its tests 10, 12, 15, 16 and 17), and the hook's one-line pin is re-aimed in
file-comments-behavior.test.ts (22), file-view-text-size.test.ts (33) and
tools/file-review-plan-anchors-states.test.mjs (5), the edit-end re-read's in
file-comments-editing-moved-latch.test.ts (4), each red there by construction.
tests/test_markdown_viewer_plan_note_slice7.py's stage rule reads a round 3 count since this round: written in round
3, its pattern stopped at round 2, the stage that round itself added to the seam suite's two mentions, so item 1's
count and the list's could disagree on it unread; every stage an item names is now the list's count for that stage and
an item names no stage the list lacks, an item's account allowed to stop at an earlier round than the list's (item 1's
file-view entry stops at round 2 where the list counts four added in round 3); the module keeps 5 cases, its premise
case requiring both mentions of the seam suite to count round 3; red over the plan of 9c4fceac5 with item 1's seam
round 3 count changed from two to one, the list unchanged, where the round 3 module is green, and green over the plan
as written. Closed as recorded, no words added: the regions layer's wrap of a `<picture>`'s img, its record in the
round 2 paragraph re-filled above, the code byte-identical to 462ad3ccf. Pre-existing, identical on main, routed (low,
found by the check for the render catch and the Raw rows): the map keeps one source table keyed on the text alone
(`sourceCache` and `sourceTable` in anchor-map.ts, the cached entry answered whenever its `source` is the text; the
lines byte-identical to 462ad3ccf, and the slice's four hunks in that file, the label control, `refuse`,
`rawOffsetToLine` and `holdsContent`, nowhere near them), `placeTokens` records a throw from marked's lexer as the
table's `lexError`, and `buildSourceTable` then answers one span over the whole file. A paint whose render throws
inside the lexer builds that table when the seat reads the reader's place over item 1's fallback rows
(reader-place.ts's `readPlace` over `sourceBlockSpans`, then `sourceTable`, in the same synchronous `renderBody` pass
as the render's own lex, so the fault must throw at both calls), and nothing drops it: the Rendered click once the
fault is gone renders the note (item 1's retry), but every later place read over the same text answers the one-span
table, so the Rendered and Raw switch no longer keeps the passage until a landing brings different bytes. Measured in
headless Chromium over the Files bundle (the pane, 900 by 700, a 40-paragraph note, marked's `Lexer.prototype.lex`
made to throw through the first paint and restored before the click): after the heal `sourceBlockSpans(text).length`
is 1 with no new lex call, and the reader at paragraph 20 lands at paragraph 28 on Raw and at 29 on Rendered again; a
never-faulted open keeps paragraph 20 across both clicks with 41 spans; a lexer that throws once, at the render's call
alone, leaves the seat's lex to succeed, 41 spans and the place kept; the same numbers on 462ad3ccf, whose catch
seated over the source text through the same table. Not a comments regression (the panel's Rendered pairing over the
healed render paints in `.fileview-md`) and outside this slice's items. The follow-up: `sourceTable` answers no cached
entry whose `lexError` is set (a still-failing lexer throws before any placing, so the rebuild per read costs little
while the fault stands, and the first read after the heal rebuilds the table once and caches it), or the healed paint
drops the entry; with a node case in anchor-map.test.ts over a lexer stub that throws through one build and then
answers, `sourceBlockSpans` counting the note's blocks after the heal, red over a `git archive` of 9c4fceac5.
Pre-existing, identical on main, routed (low, found by the check for comments regressions): with the Comments panel
open over a README-shaped note (an `<img ...><div align="center">Caption words</div>` on one line, a `<picture>`, a
table with a formula cell, a py fence, a `$$` display block, an svg figure and a `<details>` block among forty
paragraphs), a drag on the words of the plain paragraph after the fence and the float's Comment are refused as "a
block whose rendered text does not match the file" at 300, 500 and 800 px, on 9c4fceac5, 75ad5d042 and 462ad3ccf
alike, where the same drag on a plain note quotes and saves. The fence and the formula are not the cause: variants
without the table's formula, with a js fence, without the `<picture>` and without the `$$` block refuse the same
paragraph, and only dropping the one-line img-and-div paragraph maps every paragraph. marked 12.0.2 lexes that line as
a `paragraph` token with inline html (the `<img>` is not a block-level tag and its open tag is not followed by
whitespace alone, so neither HTML-block condition holds; verified over the repo's marked) and emits `<p><img ...><div
...>Caption words</div></p>`; the parser closes the `<p>` at the `<div>` start tag and mints an empty `<p></p>` for
the stray `</p>`, so one source block renders as three top-level nodes, and the one-to-one pairing in
`analyzeRendered` (unchanged by the slice) runs two nodes behind from there: that block takes the `<p>` holding the
img and is refused, the next paragraph takes the div, the `<picture>` block the empty `<p>`, and every block after
takes the block before's element, refused as not matching, until the `<details>` html block resyncs on its own element
through `nextAnchor` and swallows the nodes before it (the display formula, two paragraphs, the svg figure's `<p>`),
refusing those two paragraphs as an HTML block: eight blocks refused, the panel's state making no difference
(identical closed and open) and item 2's label making none (the `<p>` holding the img carries the label's text on this
branch, a control both walks skip, and is empty on main; the same pairing). This is the shape the Slice 5 note records
as not modelled and left to the resync, a start tag's implied end tags in a block's inline html, in a new instance (a
`<div>` start tag rather than a `<button>` or a `<select>`; `P_CLOSERS` models the end tags the parser honours through
an open `<p>`, not a start tag's implied `</p>`), and a different token kind from the README shape the build's pairing
fix covers under item 2 (`<img>` on its own line, then the unclosed `<div>`: an `html` block). Routed to the
anchor-map follow-ups of Slice 5: model the implied `</p>` of a block-level start tag inside a paragraph's inline
html, the block's `dom` taking the `<p>`, the element and the minted `<p>` as `Block.minted` does for a wrapper's
closer, with a node case in anchor-map.test.ts red over a `git archive` of 9c4fceac5. Pre-existing, inside item 4's
never-doubled default, routed (low): a file with two leading BOMs loses one on every save through both doors and its
edit entry shows a first-line hunk over a line nobody touched; recorded in item 4 with the browser's one-strip
measured, a comment at the kernel's rule, no code change in either door. Left open from the earlier rounds:
`trackedEdit.begin()` reading `seedOf(status)` without `textCurrent`, and the `where:` line's length; and from this
round, a fetch the panel did not ask over a standing pane (item 3's first recorded edge). The changes-review2 suite's
count reads 23 in every mention of this note, this round's two cases included, as the head's rule has it. Tests, by
file, this round: file-comments-changes-review2.test.ts (23, two new, three re-aimed), file-comments-behavior.test.ts
(22, one pin re-aimed), file-comments-editing-moved-latch.test.ts (4, one pin re-aimed), file-view-text-size.test.ts
(33, one pin re-aimed), tools/file-review-plan-anchors-states.test.mjs (5, one pin re-aimed),
file-view-fell-wrap-browser.test.ts (1 leg, new), fileview-parity.test.ts (4, one head added),
tests/test_markdown_viewer_plan_note_slice7.py (5, the stage rule extended); every new case that changes behaviour red
over a `git archive` of 9c4fceac5 at the assertion its file's report names (the five above; the leg's computed value;
the module's stage rule over that tree's plan under the mutation), every re-aimed pin red there by construction, the
typecheck clean after every edit, and the round's full runs (the full npm test, CI's tools step, the pytest modules)
recorded in the build report outside the repo.

**Review round 5** (2026-09-15). The review of the branch at 30b34a0db over main 462ad3ccf, under the plan of rounds 1
to 4 (the branch read by the round's checks and the finding round 4's re-check left open read again, every finding
checked by one second reader for a low and by two for a medium or a high, the fixes made one hand per file, one
consolidation commit, "Slice 7: review round 5 fixes") and the rule round 1 judged by. No behaviour changed this
round: its findings are two corrections to this note, a doc comment at one site for two pre-existing edges, and two
closures of pre-existing edges already on the books. The corrections, each in its place above: the round 4 paragraph
gave the token line's height at the dress fix as 90 to 125 px "in the modals", where the chat modal and the pane
measure 90 to 125 and the feed modal 86 to 120 (the build report's numbers, and a fresh headless run's over the three
surfaces); the sentence names the surfaces, the paragraph re-filled at width with its line count kept, every later
line number of this note unmoved. The round 3 paragraph counted the slice's lines naming `awaitBytes` as three, all
comments, a count true at that round and one short since round 4's comment at `refresh(slot)`'s end; the clause now
says every line the slice adds naming it is a comment, which holds at this head (four such lines at d617bcf67, this
round's commit, whose comment at `bytesLate` pointed at the method by its place, "the method above", not its name).
Closed as recorded, no words added: the regions layer's wrap of a `<picture>`'s img (raised a fourth time, from a
fresh Chromium probe over this head and 462ad3ccf, the label leaving at the panel's open and returning at its close on
both), its record in the round 2 paragraph, file-comments-regions.ts byte-identical to 462ad3ccf and the record
checked true of it this round (`figureAnchor` climbing both wrappers, the label's `load` handler removing it,
`tagNameOf` answering IMG); and the map's one source table keyed on the text alone, which round 4's re-check listed as
not fixed, the state the rule for a pre-existing edge intends (recorded and routed, not fixed): its record in the
round 4 paragraph, `sourceCache` and `sourceTable` byte-identical to 462ad3ccf and the slice's four hunks in
anchor-map.ts nowhere near them, checked true of this head; the re-check's landing of paragraph 26 for the second
Rendered click and the paragraph's 29 are two probes' measurements, both in the build report, and the paragraph keeps
the probe it quotes. Pre-existing, identical on main, not a new defect (low; two titles from the checks for figures,
hooks and the seam and for comments regressions, one mechanism, the round 3 paragraph's `awaitBytes` routing): since
round 4 the bytes row's Reload over a standing pane reaches the re-arm that paragraph records. With its fetch stalled
and the poll re-asking status each tick (a sidecar a session keeps writing), every status arms the 15 s deadline
afresh, so the loader stands at the head of the cards with no row and no Reload for as long as statuses land under 15
s apart, the body's pane saying only the earlier failure, and the row files 15 s after the last status: measured in
headless Chromium at this head, 13 statuses over 32 s with the loader up and no row throughout and the row 15.0 s
after the writes stopped, the same over a healthy view whose file moved under the poll, and the same on 462ad3ccf; a
quiet poll files the row at 15 s as item 3 says. Before round 4 this path filed the failure row at the first status,
the misleading words round 4 fixed, and never reached the re-arm. The follow-up stands as round 3 routed it (arm once
per reload asked, or re-arm only on a new file mtime, with the mock-timer scene it names), not taken in the fifth of
six rounds: one timer per wait against one per status is main's deadline semantics, reviewed afresh if changed.
Pre-existing, recorded, not changed (low, the check for comments regressions): the late-failure variant of item 3's
deadline-tail sibling. The row's Reload whose fetch stalls past 15 s and then fails leaves the deadline row's tail,
"the view still shows the earlier text", over the new pane's words: paintAll's head needs the wait, which `bytesLate`
ended, and `syncFailedRow` reads failure rows alone; measured in headless Chromium at this head, the 500 released
after the deadline, the pane and `error()` reading the new words and the row unchanged 3 s later, where the same fetch
failing at once or at 5 s re-words the row (the controls). 9c4fceac5 re-worded the row off the new pane (its row was a
failure row filed at the status, the round 4 bug), and 462ad3ccf ends the same sequence with no row at all (its
`refresh` finally dropped the "bytes" mark at the status's landing, so `bytesLate` filed nothing) while filing the
same tail over a pane under a quiet poll: the tail is pre-existing, the path to it new since round 4. A tail read off
`error()` at the tick or at the later pane's paint needs new wording (BYTES_FAILED_TAIL's "that failure" refers to
parenthesised words the deadline row lacks): the owner's wording decision round 4 recorded, which stands. Both edges
are named at the site since this round: `bytesLate`'s doc comment in file-comments.ts says the timer is armed afresh
by every status that lands while the wait is up and that the row's tail is not re-read against a pane that lands after
the deadline, pre-existing, recorded here and routed; no behaviour changed, no test added (nothing to fail before),
and the ledger's `where:` line names the comment. Left open from the earlier rounds: `trackedEdit.begin()` reading
`seedOf(status)` without `textCurrent`, the `where:` line's length, and a fetch the panel did not ask over a standing
pane (item 3's first recorded edge). Tests, by file, this round: none added, none changed; the typecheck clean after
the comment, and the round's full runs (the full npm test, CI's tools step, the pytest modules) recorded in the build
report outside the repo.

**Review round 6** (2026-09-15). The review of the branch at d617bcf67 over main 462ad3ccf, under the plan of rounds 1
to 5 (the branch read by the round's checks and the finding round 5's re-check left open read again, every finding
checked by one second reader for a low and by two for a medium or a high, the fixes made one hand per file, one
consolidation commit, "Slice 7: review round 6 fixes") and the rule round 1 judged by, in the sixth round, the cap the
review ran under: a regression, a wrong landing, a wrong mapping, a comments regression or a failure case showing a
blank or a bare glyph is fixed with a test failing before over a `git archive` of d617bcf67, every other low is
recorded in this note in one sentence (the scene, the mechanism, why it waits), and after this round only a wrong
mapping, a comments regression in the Rendered view or a failure case showing a blank or a bare glyph reopens the
review (the owner's rule). No behaviour changed this round and no test was added or changed (nothing to fail before):
its findings are two edges recorded at items 1, 2 and 6 and named at their sites in file-view.ts, one correction to a
code comment in file-comments.ts, one closure of a pre-existing edge already on the books, and one correction to this
note. Recorded, not changed (low): an empty file whose render still threw shows two lines over the empty rows' root,
item 6's first and item 1's `RENDER_FELL` line second, since the prepend runs after the catch in both viewers; only a
sanitizer or DOM-pass fault throws over "" (marked and DOMPurify accept the empty string), both sentences are true and
nothing is blank, so the order stays as landed and an order rule waits for a fault that shows itself; the measurements
are at item 6, the exception is noted at item 1, and the site is named in `renderFellLine`'s and `RENDER_FELL`'s docs
and both viewers' prepend comments. Recorded (low), and fixed in the closing pass below: two imgs under one anchor, in
one `<picture>` an author types or in one `<span class="fc-imgwrap">`, got one label after it naming the last of them
to fail and the `load` of either removed it while the other still failed, leaving that figure the browser's own
rendering alone; `figureAnchor` climbed a `picture` and the class without asking what either held, since the layer's
own wrap holds one img, so a `<picture>` the sanitizer keeps reached this with no class (this paragraph and item 2
first said the panel's private class alone reached it; corrected after the round, with the `<picture>` scene measured
at f2c422709 added to item 2), and main drew no label for such a figure at all; the measurements are at item 2 with
the fix (the anchor climbing a `picture` or a wrap only when it holds one img alone), which this round routed as a
follow-up reviewed afresh since anchor-map.ts reads such a span as one IMG, and which the closing pass took; the site
is named in `figureAnchor`'s doc, which names the span and, since the closing pass, the picture. Corrected at the
site: round 5's comment at `bytesLate` pointed the re-arm at "the method above", which is `bytesLanded` (the method
that ends the wait), not `awaitBytes` (two methods up, the one that runs `clearTimeout` then a fresh `setTimeout` on
every status whose file mtime is not the view's); the comment names `awaitBytes`, a name rather than a position, which
a later insertion cannot rot, so the slice's lines naming it in file-comments.ts are five at this head, every one a
comment, and the round 3 paragraph's clause holds unchanged; the round 5 paragraph's count clause above is re-worded
to read at its own commit (four such lines at d617bcf67, the comment pointing by place), where it had said the comment
named no method; `awaitBytes` itself stays byte-identical to 462ad3ccf. Closed as recorded, no words added: the
deadline armed afresh by every status that lands while the wait is up, which round 5's re-check listed as not fixed,
the state the rule for a pre-existing edge intends (recorded and routed, not fixed): its record, with the
measurements, in the round 5 paragraph, its routing in the round 3 paragraph, `awaitBytes` byte-identical to 462ad3ccf
and the round 5 record checked true of this head. The follow-ups routed by this slice's note and its review, on the
books after this round: `awaitBytes` armed once per reload asked, or re-armed only on a new file mtime; the map's
source table caching a lexer failure by text; the implied `</p>` of a block-level start tag in inline html (Slice 5's
anchor-map follow-ups); the regions layer's wrap of a `<picture>`'s img; the Reveal scroll lock; the line N+1 clamp;
the phantom Raw row; the double-BOM exact form; a seam member for a fetch the panel did not ask; and the deadline
row's tail over a later pane (the owner's wording); the anchor over two figures in one `<picture>` or one authored
wrap, routed here, left the list in the closing pass. Left open from the earlier rounds: `trackedEdit.begin()` reading
`seedOf(status)` without `textCurrent`, the `where:` line's length, and the ledger's `pr:` line once the PR exists;
the ledger's `where:` line names this round's comments. Tests, by file, this round: none added, none changed; the
typecheck clean after the comments, and the round's full runs (the full npm test, CI's tools step, the pytest modules)
recorded in the build report outside the repo.

**Closing pass** (2026-09-15). The review of the branch at 9553c666c (round 6's fix commit f2c422709 under its records
correction) over main 462ad3ccf, under the rule round 6 set: after that round only a wrong mapping, a comments
regression in the Rendered view or a failure case showing a blank or a bare glyph reopens the review, and this pass
fixes exactly one such case, the one round 6 recorded at item 2 and routed, with a test failing before over a `git
archive` of 9553c666c. Two failing figures under one anchor, two imgs in one `<picture>` an author types or in one
`<span class="fc-imgwrap">`, shared one label, and the heal of either removed it while the other still failed, that
figure showing the browser's bare broken-image glyph with no text; read as the third reopening case and fixed in
`figureAnchor` alone: a `picture`, the layer's class or a link holding the figure alone is climbed only when it holds
exactly one img (`oneImg`, a `querySelectorAll("img")` count of one), so a wrapper holding two is left as the img's
parent and each failing img's label is its own next sibling inside it, naming its own source, a second `error`
rewriting its own alone and a `load` removing its own alone (item 2 has the mechanism and the measurements); the
layer's own wrap holds THE img and is climbed as before, inside a two-img `<picture>` included, and a link's
`linkAround` already asked for one child, so every one-img figure's label stands where round 1 left it. No sheet
changed (the label's class, mark and dress are as they were), anchor-map.ts is unchanged and reads the label as before
(`isFigureLabel` by the class, both CONTROL_CLASSES lists), checked by its node suite and the wrappers and cells
browser legs; `figureAnchor`'s doc names the picture beside the span, and the follow-up left the routed list above.
Tests, by file, this pass: file-view-figure-error.test.ts (10, one new: two imgs in one picture and in one authored
wrap, a label each after its own img naming its own source, a second error rewriting its own alone, a heal removing
its own alone with the other's standing, the layer's wrap inside a two-img picture climbed and the picture not, a link
around a two-img picture not reached, and two source pins on the gate and the count; red over a git archive of
9553c666c at the first count, one label for the pair, and at the gate's pin); no other test changed. The typecheck
clean after the change, and the pass's full runs (the full npm test, CI's tools step, the pytest modules) recorded in
the build report outside the repo. After this pass the owner's termination rule stands as round 6 set it: only a wrong
mapping, a comments regression in the Rendered view or a failure case showing a blank or a bare glyph reopens the
review.

**Manager review round 1** (2026-09-15). The manager's review of fork PR 754 at 98859d061 (the closing pass's head
cce4f1377 under the ledger commit) over main 462ad3ccf, the round after the owner's six and their closing pass: seven
findings, all low, one more that did not hold, and rulings on the PR body's open decisions, every one marked fix or
keep. Under the approved rules an all-low round closes the review: the owner applies the fixes with no verify round
after them, then the manager's sweep, CI, the landing on the standing word and the deployment note (the kernel's BOM
rule in `_save_file` and `_edit_log_after` reads only at the live kernel's restart). The fixes, each recorded in its
item above with its tests, made one hand per file and landed as one commit: item 7's `changeGroups` and `paragraphAt`
counting every ending through the module's `LINE_ENDING`, a disagreement with the Reveal title, the landing cue and
the Raw rows that the review's round 1 had routed as pre-existing and this round read as the slice's own
(file-comments-model-line-endings.test.ts, 0 of 6 over a git archive of 98859d061); item 7's host `editDiff` splitting
on the kernel's line-ending set, with one fixture holding both doors to one answer, save-doors.json
(tools/file-comments-host-save.test.mjs and tests/test_savefile.py); item 4's host cap edge on a BOM file driven
through the host door over the same fixture; item 5's Latin-1 line left standing when a landing finds it with the same
words, so the live region announces once (file-view-seam.test.ts, the failures leg, four suites' pins re-aimed); item
1's Comments panel over the render catch executed in the failures leg; md-sanitize.test.ts's `setMdSanitizer` stand-in
through `hideEdges`, with a projection assertion; and item 6's file holding only a byte order mark saying so, in the
words the manager gave, keyed on the answer's byte count (file-view-seam.test.ts, the failures leg,
file-view.test.ts). The rulings on the body's open decisions, each applied and recorded above: the CR-only save
writing the lone CRs back (`norm` on the editor's view, `eolCR` beside `eolCRLF`; item 7); the `{ line: n }` open of
an empty file raising the one-line notice (item 6); `imgFailed`'s sentence hoisted as `DECODE_FAILED` for the guide's
pin (item 3); the sixth guide sentence for the panel's row, with three more sentences the same reading admits (item
8); `RAW_ROW_SPLIT` hoisted above the closure that reads it (item 7); the host's tiebreak scene driving the save verb
in place of a raw write that dropped the BOM (item 4); and editor-lazy's chunk test, red under the single-file recipe
alone, diagnosed as one over-specified key and one recipe, the recipe recorded in the test's header (item 8). Kept or
accepted as recorded: the nine older anchor-map cases on the pre-Slice 7 grid, standing inputs of the map; the
fallback count at a CRLF's LF offset, hljs coarser on a CR-only file, an authored `span.fc-imgwrap` around one img,
and the ledger's `where:` line at its length; `scripts/upstream-ledger.py set` accepting an empty value for a required
key, outside this slice and the manager's held follow-up; and the commit messages citing pre-rebase shas, history. The
finding that did not hold: that the DOM stand-in the figure suites copy is an avoidable departure, where 96 of the
repo's webview test files keep their own fakes by the shim's documented convention and this slice adds two. Records
this round: this note's sentences at items 1, 3, 4, 5, 6, 7 and 8 and the counts in every mention (the head's rule),
the guide's four sentences, tests/test_guide_files_failures.py from a record pin to a guide pin, and the ledger
entry's `where:` line naming every file this round changes, with its title and body naming the BOM-only line and the
CR-only save; CONTEXT.md unchanged, no term coined. Tests, by file, this round: file-view-seam.test.ts (58, one new,
two cases re-aimed), file-view.test.ts (59, pins re-aimed and added), file-view-failures-browser.test.ts (7 legs, two
new, one scene extended), file-view-tracked-edit.test.ts (13, one case widened), editor-lazy.test.ts (16, pins, the
replica extended, the chunk test's key read by its tail), md-sanitize.test.ts (19, one stand-in through the shim),
file-view-links.test.ts (28), file-view-outline.test.ts (15) and file-view-place.test.ts (8) with pins re-aimed,
file-comments-model-line-endings.test.ts (6, new), tools/file-comments-host-save.test.mjs (19, two new),
tools/file-comments-host-tiebreak-review.test.mjs (12, one scene rewritten), tests/test_savefile.py (26, two new, one
class over the shared fixture), tests/test_guide_files_failures.py (19, six new, three pins re-aimed),
md-url-view.test.ts (29) and file-edit.test.ts (12) with one pin each re-aimed to the new prepend and save lines,
file-comments.test.ts (35) with the seam pin's optional prepend line re-aimed to the same ternary (red in the round's
full npm test until then, the one failure beside the box-only control), and file-comments-changes-review2.test.ts and
file-comments-regions-review-3.test.ts with the stand-ins that spell the decode pane's sentence aligned to
`DECODE_FAILED`; every case that changes behaviour red over a git archive of 98859d061 at the assertion its report
names (the single-file recipe: the subtrees ui, vendor and vscode-extension's package.json, tsconfig.json and
esbuild.js, node_modules linked, the changed test copied in, NODE_PATH and the CodeMirror alias flags for the editor
suites), the cases for shipped behaviour green there by design (the panel over the render catch, red under a
`contentRoot` that ignores `mode()`; the host cap edge, red with the cap check put back over the view's text; the
tiebreak scene, red over main 462ad3ccf), the typecheck clean, every browser leg through one slot at a time, and the
round's full runs (the full npm test, CI's tools step, the full pytest) the sweep's. The review closed with this
round.

### Slice 8: a cell and a code line are commentable from Rendered (ruling 2026-09-07, decision 7)

Exact mapping for tables and fenced code: the anchor map learns how marked lays out a table cell and a
code line, so a selection made in the Rendered view inside either maps to the note's source offsets
and the highlight lands on the right occurrence; the Raw fallback stays for shapes the map still
refuses. Large; built directly after Slice 5, with Slice 5's test files extended. Acceptance: a
comment on a cell and on a code line made from Rendered paints in both views after a reload; a
selection spanning two cells is refused with the reason named.

**The Slice 8 build** (2026-09-12). Branch `mdviewer-s8`, cut from 6020e9309, the head of `mdviewer-s5` (Slice 5, fork
PR 749, in the queue when the build began), every commit on it self-contained so that the branch could rebase onto the
fork's main once Slice 5 landed (the alternative of the brief's open question 1, taken so the build could start before
that landing). After the review's round 1 it was rebased onto main 696229f84, the merge of PR 749, and after the
review's closing pass onto main 929ae86e1, the merge of PR 750, the branch's base since (fork PR 752); the two mains
differ in none of the files the slice touches (kernel/judge.py, two kernel tests and a ledger entry lie between them),
so a rule identical on main 696229f84 below is identical on 929ae86e1. Each rebase re-minted every commit, so the shas
the commit messages, the test files' headers and the round records name are trees no clone of the fork reaches, and a
citation below of a tree a case fails over names the commit on the branch as it stands (the review's round 2 after the
first rebase, the PR review's round 1 after the second). The mapping, which `git range-diff` over the lineages reads
as the same patch commit for commit: the build's head is cd3a06501 on the lineage cut from 6020e9309, c68f52212 on the
one rebased onto 696229f84 and 7201d7954 on the branch; round 1's fix commit is 3865ec2f4, d8a55bb7e and 499ec377f
likewise; the rounds from 2 on ran on the second lineage, so each has two shas: round 2's fix commit 2136fa7d2 is
e2cd869cb on the branch, round 3's 90c6ff242 is 2dba77427, round 4's 8ae3fda02 is 473307626, round 5's 43dbcc722 is
5d9e4ae43, round 6's b69116e26 is 3b6950074 and the closing pass's 20c2fcbe3 is ef030de94. The review's round 2 also
changed two rules items 4 and 5 describe
as built: a display formula's hole ends at its closing delimiter, so the exact quote of a quoted `$$` block covers the
formula, and a fence whose lines all show nothing places a change's point by its `<pre>`'s order among the block's.
Its round 3 changed seven more, each recorded under its item below: a table whose raw ends with its last row's last
character ends there for a change's point too, so a point at that row's end keeps its card (item 1); the one-cell rule
counts a cell holding a formula alone (item 3); a fence's folded trailing blank line places at the end of the pre's
last row, a fence the note ends inside right after its opener keeps the note's end card-only, and a CRLF ending's two
bytes are one position (item 4); a stamped formula box's arrivals dot comes off in print (item 5); and, a pre-existing
behaviour of the comments feature fixed in this slice, a drag begun on a highlight's first glyph selects the passage
(item 2). Its round 4 changed more, each recorded under its item below: every cell whose source holds something has a
record, a cell holding a formula alone among them, so the one-cell rule counts two formula-only cells, offers the Raw
view on the table's covered cells, widens the pass's offer by a formula the selection covered whole in the same table,
and refuses two formula-only cells selected alone before the formula's rule does (items 1 and 3); a change's point
inside a cell places against the cell's own characters alone, and a table or a fence that begins a list item places
its point before its first character, not after the previous item's text (items 1 and 4); a container's indent or
marker before a nested fence's first content line is that line's (item 4); the CRLF rule's reach outside code is
recorded and pinned (item 4); and a display formula's stamped box takes the keyboard back after a repaint (item 5).
Its round 5 changed four more, each recorded under its item below: the one-cell rule counts a table's cells by source
span against the selection's span, so a formula-only or picture-only cell the drag ran through counts wherever the
drag's ends fell, and the offer is the covered cells' span (item 3); a fence's closer edge is the fence's own, a point
on the last code line's trailing whitespace or at its line feed sitting after the last code character whatever follows
the fence (item 4); a table's or a fence's start edge places after the same item's prose alone, never after another
table's or code block's characters, and a block with no positioned character where the rule looks, a table whose first
header cell shows nothing or a fence whose lines all show nothing, keeps its first character's point on its card
(items 1 and 4); and a cell the per-cell fallback holds keeps its edge points on the card, round 4's rule pinned (item
1). Its round 6, the landing round, changed three more, each recorded under item 4: an inner code line's trailing
whitespace and line feed place after the line's last character in its own row, where the point sat one row down since
the build; the trailing whitespace and line feed of the prose line before a nested fence or table place after the
prose, the Raw view's row, where round 5 had put them in the fence's first row or the first header cell; and a fenced
block the reading could not place counts for the start edge, and a point inside a hole before a placed block keeps its
card, where round 5's search latched onto the later fence. Its closing pass, at the review's cap of six rounds,
changed one more, recorded under items 1 and 4: a table or a fence after a line holding no positioned character, a
formula alone or a picture alone in its own item or quote, keeps the point of that line's ending, of the blank line,
of the indent and of its own first character on its card, as main did, where rounds 2 to 6 painted it inside the
block. The PR review's round 1 (2026-09-13, over the head 4a3e18664; the test headers call it the landing round)
changed two more, both recorded under item 4 and both keeping the card where a point has no exact position in the
block: the line feed that ends a fence's closer line, which the lexer leaves off the fence's raw when a blank line
follows the fence or the fence ends its list item or its quote, keeps its point on its card at the top level, in a
quote and at an item's end, where rounds 2 to 6 placed it after the last code character, or before the next item's
text when the fence ended a non-last item; and the outer line's line feed, the sub-item's indent and marker and the
table's first character, at a sub-item's table under an item holding a formula alone, a shape the closing pass
recorded and left placing in the first header cell, keep their points on their card, the card kept wherever the
placement is not the cell's own text exactly. The PR review's round 2 (2026-09-13, over the head c4a225379) applied
that rule to the shape's neighbour and to its sibling case, both recorded under item 4: under an outer item whose
text precedes a formula alone, a sub-item's table's points from the blank line after the text through the formula's
bytes, the blank line and the sub-item's indent and marker to the table's first character keep their card, where
round 1 painted them into the first header cell (its rule read no further once an enclosing item held a positioned
character before the block) and main placed them after the text, never in a cell; and a formula-alone item followed
by an item that begins with a table places its marker and pipe before the first cell's text at every nesting, the
top level, nested in an item and in a quote alike, where round 1 kept the card for the nested and the quoted list
alone, counting the sibling item's formula through the nested list's element, a sibling item's content being no part
of the rule. The items below are numbered as the build was planned: 1 the cells, 2 the code lines, 3 the one-cell
rule, 4 the change marks and the deletion points inside a fence or a table, 5 the
display formula under a highlight (the Slice 4 note's item 10, routed here through the Slice 5 note's (e)), 6 the
records; a reference to an item below is to that numbering, and "the brief" is the Slice 8 build brief of 2026-09-11,
whose fifteen open questions are cited by number with the default the build took. The standing rule for the build:
these changes cause the file-comments feature no trouble, which item 6's last entry states as the guarantees every
test family re-verifies. Where the code as built departs from the text above, why, and which test holds each rule:
1. *Item 1, a table cell maps from Rendered.* A table was one hole over its raw in the anchor map: every cell's text
   went through `putHole` with a negative position, so a selection in a cell refused as "touches a table" with the Raw
   view offered on an `indexOf` of the selected text, and a change inside a cell painted through the fallback's
   ordinal (the Slice 5 probe's section (j)). Now `walkTable` (anchor-map.ts, on the Walked row) re-cuts each row of
   the raw as marked's `splitCells` does (`rowCells`: the segments between the pipes an even count of backslashes
   precedes, a blank first and a blank last segment dropped, a body row cut to the header's width and padded), trims
   each segment as the cell's text is trimmed, verifies it against marked's text with `\|` unescaped (`cellView`, a
   View mapping the cell's text index to the row's, one more for every escape before it) and walks the cell's inline
   tokens over the cell's own characters (`walkRow`), the header's cells then each row's left to right, the renderer's
   order, so the block's `chars` are byte for byte what `putHole` gave and the `<table>` pairs as before: only the
   positions change. The Emitter records each cell's extent among the chars with its trimmed source span (`Cell`), one
   for every cell whose trimmed source holds something, a cell holding a formula alone or a picture alone with an
   empty character range (the review's round 4; before, such a cell had no record, so the one-cell rule, which counts
   the records, never saw two of them in one span: item 3), and each table's span (`TableSpan`), carried onto the
   Block beside `holes`. A cell's constructs are a paragraph's: a code span, emphasis, a link or a highlight emit
   positioned characters; a formula or a footnote reference is a hole inside the cell, so a boundary in it refuses
   with the formula's sentence and the Raw offer preselects the formula with its delimiters, and a Raw comment over a
   cell holding a formula paints the cell's text around it (the two findings the Slice 5 review's round 2 routed here,
   the Slice 5 note's item 10 (j), closed by this); a picture emits nothing, so a cell holding one maps where
   `plainInline` refused the whole table. A cell the reading cannot place is a hole of its own with the Raw offer, the
   cells beside it mapping (the brief's open question 9, the default): the walk's sentence where the walk refused
   ("prose with an HTML entity", the sentence the whole table read before), the table's where the re-cut is not
   marked's text; its shown text is `plainInline`'s, or the entity decoded, so the pairing holds; a hole's characters
   are counted per UTF-16 code unit as positioned text is (`putHole`; the review round 1: iterated by code point, an
   astral character in a hole cell, an emoji beside an entity or a numeric reference decoding to one, left every later
   cell of the table one code unit off, so a Save from a later cell stored a quote running over the pipe into the next
   row, a wrong mapping; anchor-map-cells.test.ts and anchor-map-cells-browser.test.ts hold the fix). A raw with fewer
   lines than the token's rows, or a row whose cell count the re-cut cannot produce, keeps the whole-table hole
   (`tableHole`, and `walkRow`'s refusal that routes to it); marked's own tokenizer produces no such shape, so the
   hole is reached under a table tokenizer override alone, as `walkCode`'s is under a `fences` one (the PR review's
   round 1: before, no test reached it and a deleted `tableHole` call left every suite green;
   anchor-map-cells.test.ts's seventeenth test hands the walk, through a `table` tokenizer override for a marker
   header cell, a header token with one cell more than the row's pipes cut, `walkRow`'s refusal, and a token with
   three rows more than the raw has lines, the count before the walk, and holds the refusal with the table's sentence
   and the Raw offer on the selected text, a two-cell drag refused the same way, a Raw comment painted by the
   fallback's ordinal, a change's point inside a cell on its card and the prose around the table mapping, the same
   note under marked's own token the control). A padded
   cell shows nothing; a truncated row's tail past the header's width is not rendered
   and stays unpositioned, so a Raw comment on it paints nothing and keeps Reveal, as a fence line's does (open
   question 14, the default). The right occurrence: a table with two identical cells maps the selected cell, since the
   positions come from the emission order and `descend`'s count under the `<table>`, not from a text search, and a
   stored comment paints through `anchorAt` and `nthNonWs`; a positionless comment on a repeated cell keeps Slice 5's
   sequential hint. Two edges the rules already had now reach cells: a Raw quote spanning a cell the per-cell fallback
   holds and a positioned cell paints the positioned cell alone through the exact path's first and last positioned
   characters (before, the fallback painted both), while a quote on the hole cell alone still paints through the
   fallback (the Slice 4 note's edge rule, open question 11); and `renderedSpot` places a deletion point inside a
   cell's span against the cell's own characters alone, before its first or after its last, a cell with none (a
   formula alone, a hole cell) keeping the point on its card (the review's round 4; before, a point inside an inline
   formula that ended a cell's text, past the cell's last positioned character, read the block's next positioned
   character and was painted in the next cell, or in the next row's first cell, a cell the change is not in), and
   keeps a point elsewhere in the table's raw (the delimiter row, a pipe, a row's line feed) on its card, and one at
   the table's end where its raw ends with the last row's last character and not the row's line feed (a table that
   ends its quote or its list item, whose trailing line feed marked trims off the container's text, or the note with
   no final line feed; the review's round 3: before, that offset lay outside the table and the point sat after the
   last rendered cell's text, in a cell the change is not in, a truncated row's unrendered tail at the starkest; a raw
   ending with its line feed keeps the end of the file after it at the block's end, after the last cell's character,
   as after a paragraph's; `TableSpan.endsLf`, anchor-map-rendered-points.test.ts's second test), never beside the
   words after the table, a point at or before the table's first character sitting after the text before the table
   when the block holds such text in the same list item, or in no item (a quote's text before its table; `edgeSpot`),
   that text being prose and not another table's or code block's characters (the review's round 5; before, two tables
   in one item with nothing between placed the second's point inside the first's last cell, after `b`, and a fence
   after a table or a table after a fence inside the earlier block's cell or row), and, at a top-level table's, whose
   block holds nothing before it, or at a table that begins a list item, where the text before it is the previous
   item's, before the first header cell's first character, the block's or the item's edge, as a top-level fence's
   opener sits before the code's first character (before this slice that point kept its card, the table a hole; the
   review's round 2 recorded it, anchor-map-rendered-points.test.ts's first test extended with both tables; its round
   4 the item that begins with a table, before which the point was painted after the previous item's text, inside that
   item's table's last cell when it was a table too, and the same for a fence that begins an item, the file's third
   test; its round 5 the first header cell that shows nothing, a formula alone, a picture, an empty cell or the
   per-cell fallback's hole, whose table's first character keeps the point on its card as a point inside such a cell
   does, where rounds 2 to 4 placed it before the table's first POSITIONED character, the second header cell's or the
   body row's first cell's, and the table of formulas alone or of pictures alone that begins an item, whose point
   round 4 placed after the previous item's text, inside that item's pre or its table's last cell, or before the next
   item's, main having kept the card after a fence or a table item; anchor-map-block-edge-points.test.ts, item 4),
   and, the item's or the quote's content before the table a formula alone or a picture alone, no positioned character
   of the item's, on its card (the review's closing pass; item 4). A cell that begins with an escaped pipe maps its
   whole-cell quote from the pipe, without the backslash (`\| lead` stores `| lead`, `\|` alone `|`), and the one-cell
   offer for a span begun in such a cell starts there too: the inline walk positions an escape's shown character at
   the escaped character's index, Slice 5's convention for every block (anchor-map.test.ts pins the rendered `*`
   mapping to the source `*`, not the backslash; a paragraph's `\# not
   heading` maps `# not heading` on main 696229f84 too), an interior or a trailing escape staying inside the quote
   with its backslash; recorded by the review's round 5 and routed to a follow-up (an escape at a selection's edge
   taking its backslash), the cell mapping being no place to change a walk-wide convention. A table-part tag inside a
   cell (`<td>`, `<th>`, `<tr>`, `<thead>`, `<tbody>`, `<caption>`, `<col>`, `<colgroup>`) with text after its closer
   makes the browser's parser restructure the table (the text foster-parented before it, the row split), so the
   block's nodes no longer pair with the walk's blocks and the table and every later block of the note refuse as a
   block whose rendered text does not match the file, and `<plaintext>` in a cell removes the rest of the note from
   the Rendered view: identical on main 696229f84, the pairing's and the sanitizer's, outside this slice's items, the
   refusal the safe direction; recorded by the review's round 5 and routed to a follow-up (the pairing re-synced after
   a restructured table, or the sanitizer dropping a table-part tag out of place); the other inline-HTML shapes probed
   in a cell (a nested `<table>`, `<template>`, `<select>`, `<iframe>`, `<textarea>`, `<xmp>`) refuse the hole cell
   alone with the entity sentence, the cells beside it mapping. A mark's `padding: 0 2px` inside a cell (open question
   15, the default: accept and measure): the table is `width: max-content`, each column as wide as its widest cell's
   content, and the padding adds 4 px to the marked cell's, so a mark in a column's widest cell widens a table under
   its `max-width` cap by 4 px, 4 px more per nesting level, and a mark in any other cell of the column widens
   nothing. Read in Chromium at pane 900, at pane 380 and in the chat modal at 1000, the same at each: on the probe
   fixture's two-column table (anchor-map-fixtures/wrappers-plain.md, where `cell three` is the first column's widest
   cell) 173.4 px bare and with `cell one` marked, 177.4 px with `cell three` marked; on a table whose marked cell is
   its column's widest, 158.9 px bare, 162.9 px with the cell marked, and 170.9 px when a quote over the whole row
   marks both cells and a second comment on the first cell nests in it (8 px in that column, 4 in the other). The
   build's record of 173.4 px both times was the fixture's `cell one`, the narrower cell's case; the review round 1
   re-measured. So a comment on a column's longest cell moves the table's right edge by 4 px when the panel opens or
   the comment lands; the padding is the comments feature's standing mark, and the layout-neutral mark (the Slice 5
   note's item 10 (f)) stays the owner's standing call about the comments feature. A mark's side padding inside a
   fence row (the review round 1): the `.fc-hl` and `.fc-presel` rules' `padding: 0 2px` moved a Rendered code row's
   characters 2 px right from the mark's start and 2 px more after a mid-line mark's end (column 7 at +2.02 px and
   columns 14 and 19 at +4.02 after a mark over `ghijkl`, every column +2.00 under a whole-row mark, at pane 900 and
   in the chat modal at 1000 in Chromium; the same numbers on 6020e9309 through the fallback's paint, so no
   regression), so a commented line stood out of line with the rows above and below it while the comment stood. Both
   sheets now carry `.fileview-md pre .fc-hl, .fileview-md pre .fc-presel { padding: 0; }`, a fileview-parity head:
   inside a fence the mark's box is the marked characters' own cells and the wash and ring sit on the selected columns
   (a mark over `abcdef` 43.36 px wide where it was 47.36, its height 14 px unchanged; a blank row inside a spanned
   quote takes no mark on either tree, so nothing is hidden). Prose marks keep their padding (the layout-neutral mark
   stays the owner's call) and the Raw view's rows, which carry the same 2 and 4 px shift, are unchanged, a call for
   the owner. One visible consequence: the arrivals dot (`[data-new]`, a radial gradient at 3px 3px) sits over the
   first glyph's top-left corner in a code row, not in the padding. styles-fc-hl-code-row-browser.test.ts (1 leg, new:
   two served comments over a three-row fence, one on a word of the first row and one on the whole third row, every
   column's x read per row at pane 900 and in the chat modal, then a real drag over a word of the second row whose
   pending target leaves the columns in line too) holds it, red over a git archive of 7201d7954, the build's head, at
   column 0. anchor-map-cells.test.ts (18, new, over the new synthetic fixture anchor-map-fixtures/cells.md: a header
   and a body cell, the second of two identical cells, aligned columns, `\|` in a code span and alone, markup in a
   cell, a formula and a footnote reference in a cell, padded and truncated rows, tables in a list item, a quote and a
   `<div>` wrapper, the entity cell's fallback, the one-cell rule's shapes, one cell into prose, the boundary
   whitespace, the paint and the deletion points by position, the shapes marked accepts, the 1,000-row table timed, an
   astral character in a hole cell leaving the later cells their own offsets, the one-cell rule counting a cell
   holding a formula alone and a formula that begins a cell's text, the review's round 3, and the two-table shape's
   both outcomes, the review's round 4; and `tableHole` under a tokenizer override, the PR review's round 1),
   anchor-map-cells-formulas.test.ts (6, new, the review's round 4: a deletion point inside an inline formula that
   ends a cell's text placed in the cell's own row and cell; the one-cell rule over formula-only cells, from the prose
   before a table into an all-formula header row and across two formula-only cells into the prose after; the pass's
   Raw offer widened by a formula covered whole in the same table and not by one in another table; two formula-only
   cells selected alone refused by the one-cell rule; and the review's round 5: the count by source span, a
   formula-only or picture-only cell the drag ran through counted wherever the drag's ends
   fell, from the prose before a table through an all-formula header row into a body cell, from a positioned cell
   through a trailing formula-only or picture-only cell into the prose after, a whole table of formulas, two tables,
   the offers reaching the formula-only cells, and the text twins, the pad-to-pad drag, the drag to a cell's pad past
   a picture, the empty trailing cell and the last-cell-into-prose rule as controls) and
   anchor-map-cells-browser.test.ts (6 legs, new, over the real viewer and panel: a real drag over `cell one` at pane
   900 and 380 and in the chat modal, the composer's quote and Save, the posted anchor the exact slice at the cell's
   offset, the mark in the `<td>` and on the Raw row, a fresh open painting both views; the two-cell drag refused with
   item 3's sentence and Switch to Raw preselecting the row's span; the width read; the table timed in Chromium; over
   a table with an emoji in a hole cell, a served comment and a served deletion on later cells painting in their own
   cells and a real drag's Save posting the cell's own slice; a real drag from the paragraph before a table into the
   second formula of an all-formula header row refused with item 3's sentence, Switch to Raw preselecting `$h$ | $k$`
   and the composer quoting it with Save offered, and the same drag into the first formula mapping with the pipe, the
   review's round 4; a real drag from the positioned cell beside a picture-only or a formula-only last cell into the
   paragraph after the table refused with item 3's sentence, Switch to Raw preselecting `pl-a | ![p](x.png)` and `fl-a
   | $n$`, and the cell alone mapping, the review's round 5) hold it.
2. *Item 2, a code line maps from Rendered.* A code block was one hole over its raw the same way: a selection in a
   line refused as "touches a code block" (an indented block as "an indented code block") and a change inside a fence
   painted through the fallback's ordinal. Now `walkCode` reads the raw line by line as marked lays it out: the
   opener line, then the content lines, each the text line after the whitespace prefix the compensation took (a
   backtick opener's indent) or an indented block's one to four spaces, then the closer or the line feed the lexer
   moved onto the raw (`codeLineStarts` verifies that relation for every line and the tail), and emits each text
   line's characters at the raw line's own positions, so the block's `chars` are what `putHole` gave and the `<pre>`
   pairs as before. The placement lives in anchor-map.ts over the view it has, not in fence-source.ts, so Copy's
   module and its tests are untouched (open question 8, the default). The lexer's tab expansion carries the tab's
   source index, so a two-line quote holds the TAB byte where the rows show four spaces; a selection begun in an
   indent snaps to the first glyph and an indent alone is only whitespace (the standing rule); the Copy button is a
   control a selection run into it stops before. A selection across two lines, or from the paragraph before a fence
   into its first line or out of its last line, maps to the span a Raw selection over the same characters mints, the
   line feeds, a quoted fence's `> ` markers and the fence line inside the quote (open question 2, the default: a
   one-line restriction would be a rule the Raw view does not have). The fence lines are zero-text holes of their own
   (`FENCE_LINE`, over the opener with its info string and the closer with the line feed that ends the last code
   line and the closer's own line feed, wherever the lexer left it, on the fence's raw or one past it when a blank
   line follows the fence or the fence ends its item or its quote, since the PR review's round 1, or one over the
   whole raw of an empty fence, the closer's line feed taken the same way): no character carries them, so no
   selection touches them and no refusal reads the sentence; `renderedSpot` alone reads them (item 4). A token whose
   lines the reading cannot place
   keeps the hole it was, one over the whole raw with the code's reason, so its refusal, Raw offer and fallback paint
   stand; marked's own tokenizer produces no such shape, so the hole is reached under a `fences` tokenizer override
   alone (anchor-map-line-edge-points.test.ts, the review's round 6), as `tableHole` is under a table one (item 1).
   The row-aware reading the Slice 3 map asked this slice to choose once is not needed for the mapping: the rows drop
   only the newlines, which the walk never emits, so `descend` and `nthNonWs` see through them and the character count
   under the `<pre>` is the walk's (one reader of a row remains, the change points' placement on a line that shows no
   character, item 4). `codeLineAt` and `codeLineStart`, which the Slice 3 note's item 9 kept exported for this
   mapping with no caller in production, are deleted with their docstrings and their cases (open question 6, the
   default); `codeRuns`, `codeText` and `hayRuns` stay for the fallback's hay, and anchor-map-wrapped-code.test.ts
   (4) pins that no module under ui/webview defines or calls the two and that anchor-map.ts's header names the Slice
   8 mapping and carries neither the Slice 2 boundary sentence nor the Slice 3 sentence about the helpers. Cost (open
   question 13): over a 5,000-line fence the index build plus one map takes 76 ms and forty marks 580 ms on the
   stand-in, 122 ms and about 1,600 ms in Chromium at pane 900, about 40 ms a mark, since the exact path scans the
   block's positions and walks the pre's text nodes for every mark; over a 1,000-row table (measured in
   anchor-map-cells.test.ts and its browser leg) the index build plus one map takes 31 ms and forty marks 106 ms on
   the stand-in, 43 ms and about 350 ms in Chromium at pane 900, about 9 ms a mark, less than the fence's since the
   walk under a `<table>` meets a cell's few text nodes where the `<pre>`'s hold every line. Against the Slice 5
   note's prose numbers (7.1 ms for forty marks over a 1,000-paragraph note) both are far more than twice a prose
   block's cost per mark, so the per-row scoping of `unitsUnder` the brief named is a follow-up of this slice, not
   built here (the question said a worse number makes it a follow-up, not a blocker); a mark in a fence of ordinary
   length pays nothing a paragraph's does not. anchor-map-code-lines.test.ts (16, new, over cells.md's code section
   and fenced.md, the stand-in dressing every fence as mdBlock does: the pairing and dress control, a highlighted
   line and its parts, the second copy of a repeated line, two-line selections carrying the tab byte, a quote's
   marker and a CRLF inside the quote, the whole fence and the prose either side, an indent alone and a selection
   begun in it, the Copy label, the container shapes and a linkified URL's line, the empty fence and the fence lines'
   fallback, the paint and the change points by position, the fence lines' deletion points, the shapes marked
   accepts, tab-opened lines, the obstacle order, the 5,000-line fence timed, a point on a blank or a whitespace-only
   line in the line's own row, a CRLF note's line endings at either byte in the line's own row, the review's round 3)
   and anchor-map-code-lines-browser.test.ts (5 legs, new: a real drag over `total = a * b * 2` inside its hljs spans
   at pane 900 and 380 and in the chat modal, the posted anchor at the line's offset, the marks in row 0 and on the
   Raw row, a two-line drag posting the line feed and painting both rows; a fresh open; a drag into a tab-indented
   line posting the TAB byte; the fence timed in Chromium; three served deletion points, on a blank line, a
   whitespace-only line and a line with text, each in its own row and the Raw view agreeing) hold it. The review's
   round 3 fixed a pre-existing behaviour of the comments feature, identical on main 696229f84 and no doing of the
   slice's, here because the slice's code-line marks widened where it showed: a real drag begun on the leading half
   of a highlight's first glyph selected nothing, offered no Comment and its release opened the card, in a paragraph
   and in a code row alike, because a press on a mark, a control with a tabindex, moved the browser's focus onto it
   before the press placed its caret at the end of the text node before the mark, and Chromium extends no selection
   anchored outside the element the press focused; the panel now takes the tabindex off every mark of ours the press
   began on for the length of a primary-button press and puts it back at the release, when the innermost pressed mark
   takes the focus the press would have given it, so a click still leaves the keyboard on the mark whose card it
   opened (file-comments.ts `pressedMarks`, `unfocusForPress`, `refocusPressed`; `markRecord` shared with
   `heldMark`); a press the window's blur or a context menu ends puts the attributes back and moves no focus, a press
   whose release was never heard is reset by the next press, and a repaint that replaced the pressed mark during the
   press sends the focus to the mark's successor among `ownMarks`, three branches the PR review's round 1 found no
   test reaching, each deletable with every suite green, now pinned
   (file-comments-block-paint.test.ts's ninth and tenth tests over the stand-in: a blur and a context menu while a
   press stands, the attribute back and no focus moved, a second primary press with no release heard between resetting
   the first and the release focusing the second, a secondary button's press taking nothing off, and a repaint during
   a press, a peer's comment landing by the poll, whose release focuses the successor, a display formula's stamped box
   across a landing focusing the box; file-comments-mark-first-glyph-drag-browser.test.ts's second leg over the real
   viewer: a real press then the window's blur, a press on a nest's inner mark then a contextmenu the browser fires,
   and two primary presses with no release between, on the paragraph's mark and the fence row's);
   file-comments-mark-first-glyph-drag-browser.test.ts (2 legs, new: a paragraph's words, a nest of two marks on one
   passage and a word in a fence row, each pressed at two fractions of the first glyph's width, the marks bare of
   tabindex mid-press, the selection the passage and the float offered at the release with no card opened and the
   pressed mark focused, a plain click then opening the card and Tab then Shift+Tab returning to the mark; the second
   leg the press bookkeeping's other ends, the PR review's round 1) holds it, red over a git archive of e2cd869cb,
   round 2's fix commit, at the mid-press tabindex and, the mechanism's pins removed, at the empty selection.
3. *Item 3, a selection spanning cells is refused with the reason named, the Raw view offered on the span.* Before,
   the table's hole refused at the first selected character and the Raw offer, an `indexOf` of the tab-joined
   selection, found nothing, so the composer stayed at the refusal after Switch to Raw. Now, in
   `mapRenderedSelection`'s one pass, once a table block's selected characters are found positioned, the cells they
   lie in are counted per table (the Block's `tables` and `cells`); two or more refuse with "This selection spans more
   than one cell of a table; select within one cell, or comment on it from the Raw view." (the sentence keeps
   `a table`, the guide's shape and the `/a table/` pins) and offer the Raw view on the exact span: `rawHasQuote`
   true, `rawRange` from the first covered character's source offset to the last's plus one, and `blockStartOffset`
   that same start rather than the table's, so `rawTarget`'s search begins at the span and not at an earlier identical
   row (the model is Slice 5's `formulaExtra`). Switch to Raw then preselects `cell one | cell two`, the composer
   quotes it and Save works from Raw, with no change to the panel, whose refusal card and button already key on those
   two fields. The rule reaches any range whose positioned characters inside one table lie in two or more cells: two
   body cells, a drag from the paragraph before a table into a body cell (the header's cells lie in the span), a whole
   table (open question 3, the default; mapping a multi-cell quote with its pipes would put raw delimiters the person
   did not select into a Rendered quote, which the Slice 5 ruling on HTML wrappers declined). A range that touches one
   cell and the prose beside it maps, the row's closing pipe and line feed inside the quote as a Raw selection mints;
   a drag from a table's last cell into a formula names the formula, a positioned cell being no obstacle, and from its
   first cell the one-cell rule. A cell holding a formula alone emits no character and has no cell record, and a
   formula that begins a cell's text stands before the cell's first positioned character, so a drag from the cell
   before into such a formula's glyphs counted one cell and the covered formula's widening ran the quote over the pipe
   (`a1 | $x$`); since the review's round 3 the widened span is counted against the table's cells by source span, and
   since its round 4 every cell of the table whose source holds something has a record (item 1), so the count sees two
   formula-only cells in one span where round 3's, which counted the covered formula's own cell alone, saw one and
   mapped a drag from the prose before a table through a header row of formulas alone, or across two formula-only
   cells into the prose after, with the pipes inside the quote; two or more refuse with the same sentence and the Raw
   view on the table's covered cells, the first covered cell's start through the last's end (`coveredCells`; round 3
   offered the whole widened span, the same offer for its shapes, which lay inside the table); the pass's own offer
   widens to a formula the selection covered whole inside the same table, so a drag from a header cell into a body
   cell holding a formula alone offers the formula too (before, the offer stopped at the header's last character), a
   covered formula in another table being that table's; and two formula-only cells selected alone, in one row or in
   two, are the one-cell rule's before they are the formula's (`orFormula` through `coveredOnly`; before, the
   formula's sentence with the Raw offer on the first formula alone). anchor-map-cells.test.ts's one-cell formula
   test, anchor-map-cells-formulas.test.ts and the browser leg's all-formula header row hold it (the review's round
   4); a last cell holding a formula alone into the prose after the table maps as the last-cell-into-prose rule says.
   Round 4's count still saw a formula-only cell only through a formula the selection covered at its start or its end,
   the pass counting positioned characters, so a formula-only or picture-only cell the span merely ran through was
   never counted and the pass's offer left it out: a drag from the prose before a table through an all-formula header
   row into a positioned body cell, from a positioned cell through a trailing formula-only or picture-only cell into
   the prose after, over a whole table of formulas between two paragraphs, or from one table's cell through the prose
   between into the next table's positioned second cell mapped with the pipes and the delimiter row inside the quote,
   and a drag over `| fb-d | fb-e | $n$ |` into the prose after offered `fb-d | fb-e`. Since the review's round 5 the
   pass counts every table of the span's blocks by SOURCE SPAN against the selection's span (`cellsRule`: the first
   positioned character's offset in the first block, the last's plus one in the last, the block's whole extent
   between, widened by the covered formulas), the one rule the covered-formula check reads too, so a cell that emits
   no positioned character counts where its source lies inside the span wherever the drag's ends fall, and the offer
   is the covered cells' span clipped to the selection's; a drag ended on a cell's pad past a picture selects no
   character of that cell and maps the positioned cell alone, and an empty trailing cell, which has no record, is not
   counted (recorded). anchor-map-cells-formulas.test.ts's fifth and sixth tests and the browser leg's sixth hold it.
   A drag from one table's last cell through the prose between into the next table's first header cell, two top-level
   tables or two in one list item, is those two shapes joined and maps, both tables' pipes inside the quote as a Raw
   selection over the same characters mints; refusing it would be a rule of its own, a selection covering the cells of
   at most one table, which no text asks for (the review's round 2, recorded). Into any other cell of the next table
   (a later header cell, or a body cell, whose span holds the header's cells), or from any earlier cell of the first,
   the drag covers two cells of that table and the one-cell rule refuses it on that table's span, the Raw view offered
   there (the review's round 4; round 2's record had said a cell of the next table, which holds for its first header
   cell alone; since round 5 a formula-only first header cell of the next table counts with the positioned cell after
   it, where round 4's count, over positioned characters, mapped that drag). The check is one scan of the table's
   cells per selection. anchor-map-cells.test.ts (the four shapes with their offers, one cell into prose, and the
   two-table shape's both outcomes over the fixture's two top-level tables and over two tables in one list item) and
   the browser leg's two-cell drag hold it; anchor-map-obsidian.test.ts's first-obstacle test (31) and
   anchor-map-wrappers.test.ts (38) are re-pinned where their spans now meet the rule or now map, each flip stated
   with its before in the commit. Overturned by decision 53 of plans/file-review.md (2026-09-18): a selection across
   several cells of one table anchors to its span, the pipes and the delimiter row inside the quote, and the one-cell
   sentence, `cellsRule`, `coveredCells` and `coveredOnly` are gone from the map; this item stands as the slice's
   history.
4. *Item 4, the change marks and the deletion points inside a fence or a table take the exact path.* This follows from
   items 1 and 2 with no code of its own (open question 10, the default): an insertion or a substitution inside a cell
   or a line paints by the change's own position with no count, where the fallback's ordinal had marked it under the
   count guard, so the guard's scene, a rendering that shows the token a different number of times than the source
   does, now paints the changed cell or line (anchor-map-change-marks.test.ts, whose two tests titled for the fallback
   are re-titled for the paint by position, each with a pin only a position-based paint passes); a substitution
   covering the header row and the delimiter row paints the header cells, where before the dashes in the needle
   painted nothing; a cell the per-cell fallback holds still paints by the fallback's ordinal beside a positioned cell
   painted by position; the delimiter row and a fence's opener and closer, which render nothing, keep the change on
   its card. A deletion point inside a cell or a line places before or after the nearest positioned character of the
   cell or the row, of the cell's own characters since the review's round 4 (item 1); a point at a top-level fence's
   opener places before the code's first character, one at a nested fence's opener or in the indentation before it
   sits after the text before the fence when that text is the same list item's or a quote's, and prose, not another
   table's or code block's characters (`edgeSpot`; the review's round 4 the same-item rule, its round 5 the reach),
   and before the code's first character when the fence begins an item (the review's round 4; before, after the
   previous item's text), a fence whose lines all show nothing, or an empty fence, that begins an item keeping its
   opener's point on its card, there being no code character to place it before (the review's round 5; round 4 placed
   it after the previous item's text or before the next item's), one at the line feed after the last code line, or on
   that line's trailing whitespace, sits after that character in the fence's own item whatever follows the fence, an
   indented block's likewise (the review's round 5; round 4's same-item test, applied to the closer edge too, placed
   such a point before the next item's text when the fence ended its item and the last line carried trailing
   whitespace, while the line feed right after the last character sat after it by adjacency, and the indented block's
   point sat there on every tree before), while the line feed that ends the closer's own line, which the lexer leaves
   off the fence's raw when a blank line follows the fence or the fence ends its list item or its quote, keeps its
   point on its card, at the top level, in a quote, at a non-last item's end and at the last item's end before a blank
   line alike, the closer's line feed being no code character, so the point has no exact position in the block (the PR
   review's round 1: through the closing pass the closer's `FENCE_LINE` hole ended at the fence's raw, so a line feed
   the raw did not carry fell to the adjacency rule, which placed it after the last code character, or before the next
   item's text when the fence ended a non-last item, where main 929ae86e1 kept the card in every shape but the
   non-last item's, whose point it placed before the next item's text; now the closer's hole takes the line feed
   wherever the lexer left it; anchor-map-block-edge-points.test.ts's third test holds the shapes card-only, a
   top-level fence with one blank line after it and with two, a quote's fence with a blank line after the quote and
   one ending the note, a fence ending a non-last item, a fence ending the last item before a blank line and prose, an
   empty fence and a fence of one blank line ending an item, and the CRLF twin at either byte, with the fence a
   paragraph follows directly, whose raw carries the line feed, and the last code line's own line feed, round 5's
   edge, as the controls, red over a git archive of 4a3e18664, the PR's reviewed head), and one at a table's first
   character after the text before the table under
   the same rule or, at a top-level table's or one that begins an item, before the first header cell's first
   character, and, that cell showing nothing, on its card (item 1); since the review's round 6 a point on an inner
   code line's trailing whitespace, or at the line feed that ends it, sits after the line's last character in the
   line's own row (since the build it fell to the adjacency rule, before the next line's first character, one row
   down, or two past a blank line, where the Raw view keeps it on its line; round 5 had cured the last line alone), a
   point on the line of the prose before a nested fence or a table, past the prose's last character (its trailing
   whitespace, its line feed, both bytes of a CRLF), sits after that character, the Raw view's row, whatever block
   follows and whichever item holds it, a footnote reference ending the prose standing after the point, which sits
   after the prose's last positioned character (round 5's start edge began past that line's ending and left these
   offsets to the adjacency rule, which put them in the fence's first row or the table's first header cell, a row or a
   cell the change is not in, where round 4 and main 696229f84 had them after the prose; the same offsets before a
   sub-item's fence or before an indented block after a blank line sat so since the build), a fenced block the reading
   could not place (`walkCode`'s hole, which marked's own tokenizer never yields, so the shape needs a tokenizer
   override) counts for the start edge by its raw's first character, so a point there with a later fence in the same
   item sits after the item's text as on main (round 5's search by the opener's hole skipped it and latched onto the
   later fence, so the point kept its card, or, with that fence right after, sat before its code), and a point inside
   a hole whose characters stand before a placed fence or table in the same block keeps its card, the hole rule's
   (round 5's start edge placed it before the block's first character); since the review's closing pass a point on the
   line before a nested table or fence that holds no positioned character, a formula alone or a picture alone (a
   footnote reference alone the same rule's), from the hole's end through the line's ending, the blank line and the
   indent to the block's first character, and inside the formula's TeX, keeps its card, as main 696229f84 kept it, its
   table a hole, the block beginning neither its item nor its quote with no positioned character of the item's before
   it (`edgeSpot`'s `unpositionedBefore`; rounds 2 to 6 placed it before the block's first positioned character,
   inside the first header cell or the fence's first row, a cell or a row the change is not in, and in the second item
   after a text item, where main had placed it after that item's text); a point on a code line that shows no character
   (a blank line, one of whitespace alone) places in the line's own row, at its column among the row's whitespace or
   in the empty cell, through a per-line record on the Block (`CodeSpan` and `CodeLine`, `Emitter.codes`) and
   `renderedSpot`'s `blankCodeLineSpot`, which finds the row from the nearest line of the block that shows a character
   and the rows between (the review round 1; the build placed it before the next line's first character, one row down,
   which read as that line changed); a fence's trailing blank line, whose row marked's renderer folds, goes to the end
   of the pre's last row, the row nearest it, its line feed with it (the review's round 3; before, it fell against the
   nearest positioned character, which with blank or whitespace-only rows between stood two or more rows above them,
   so the point read as the first line changed); a pre no renderer cut into rows keeps the placement against the
   nearest positioned character; anchor-map-code-lines.test.ts and anchor-map-code-lines-browser.test.ts hold the row,
   anchor-map-rendered-points.test.ts the fallback over its undressed stand-in. A fence whose lines all show nothing
   (one blank line, or lines of whitespace alone) has no line to find the row from, so it finds its `<pre>` by order
   instead, the block's k-th `<pre>` in document order for its k-th code block (`Block.codes` records every code token
   in walk order, a token whose lines the reading could not place with no line, and the renderer emits one `<pre>` per
   code token in that order), and the row by index; a `<pre>` no code token emitted (the fill's belt for a display
   formula past its bound) makes the counts disagree and the point falls to the nearest character as before; the
   one-blank-line fence, whose text marked leaves empty as it leaves the empty fence's, is told from it by the raw
   (`codeLineStarts`), the empty fence unchanged (the review's round 2; before, such a point kept its card while the
   pre showed the row and the Raw view placed it there). A fence the note ends inside right after its opener's line
   feed (the raw its three backticks and that line feed alone) has no content line and keeps the point at the note's
   end card-only like the empty fence (the review's round 3; round 2's guard had read the raw's split artifact after
   the opener as the line and placed that point in marked's floor row); the unclosed fence whose one content line is
   blank keeps that line's point card-only, the line being one of the raw's trailing line feeds `Placed` strips and
   `ownRows` reads as blank lines between blocks, identical on main 696229f84 and routed to a follow-up (an unclosed
   fence's blank lines at the end of the note as its own rows), so the two unclosed shapes agree. A CRLF ending's two
   bytes are one position for `renderedSpot`, in every block, the LF byte placed as the CR's (the review's round 3;
   before, a point at the LF byte of an inner code line's ending fell one row down and the last line's kept its card,
   strictly inside the closer's hole; anchor-map-code-lines.test.ts's sixteenth test; outside code the same rule moved
   a paragraph's or a quote's soft break's LF byte from before the next line's first character to after the line's
   last, and a list item's line ending's LF byte from before the NEXT item's first character to after its own item's
   last, the Raw view's places, recorded and pinned by the review's round 4, anchor-map-rendered-points.test.ts's
   fourth test). A container's indent or `> ` marker before a nested fence's first content line is that line's for a
   change's point, as the bytes before every later line are (the review's round 4: the opener's `FENCE_LINE` hole ends
   right after the opener line's line feed, where it ended at the first content character past the indent, so those
   bytes fell strictly inside the hole and kept their card while the same bytes before a later line placed in its row;
   `blankCodeLineSpot` reads the first line from its raw line's start, `lineStartAt`; the opener's line feed and
   backticks and the closer's indent stay card-only; anchor-map-blank-fence-points.test.ts's sixth test, its third
   re-pinned). A deletion point inside a nested display formula's TeX or on its closer, in a quote or a list item, is
   placed before the first character of the paragraph after the formula (a table or a fence after the formula instead:
   on its card since the review's closing pass, the start edge's rule above), while at the top level it keeps its
   card: the hole rule reads a hole through its characters and a formula's hole has none; identical on main 696229f84
   and outside this slice's items (the review's round 3), recorded in `renderedSpot`'s docstring and routed to a
   follow-up (a check like the fence line's in `renderedSpot` over the formula's span).
   anchor-map-blank-fence-points.test.ts (6, new: the one-blank-line fence's point in the pre's one row and the empty
   fence unchanged; a whitespace-only line at columns 0, 2 and 4, two whitespace lines each in their own row, a blank
   then a whitespace line, the folded trailing blank line at the end of the pre's last row and an undressed pre
   card-only; the pairing by order in a list item holding an all-blank fence before or after a fence with text, and
   the count guard beside the belt's pre, the point falling to the nearest character after the item's text as on main;
   the unclosed fences at the end of the note card-only; and the folded trailing blank line behind blank and
   whitespace rows, two trailing blank lines in the one empty last row, the review's round 3; and the indent or marker
   before a nested fence's first line in that line's row, a list item's fence with a text or a blank first line and a
   quote's `> ` marker, the review's round 4) holds it. anchor-map-block-edge-points.test.ts (7, new, the review's
   round 5: a fence's closer edge with trailing whitespace on the last code line, in an ordered item, a fence item
   before a text item or a fence item, a sub-item's fence before the outer item's text, the CRLF twin and an indented
   block, with the Files pane's rows and undressed, the top-level, quote, same-item-text and last-item fences the
   controls; the trailing blank line undressed; two tables, a table then a fence, a fence then a table and two fences
   in one item; a table of formulas or of pictures alone, an entity first cell, a one-blank-line fence or an empty
   fence beginning an item, card-only, the blank line's own point in its row; a formula-first, picture-first, empty or
   entity first header cell's table start, card-only; and a hole cell's own edge points, round 4's rule; and the
   closer's own line feed in every shape, the PR review's round 1) holds the round 5 rules and the closer's.
   anchor-map-line-edge-points.test.ts (6, new, the review's round 6: the line before a nested fence or
   a table at every offset past the prose's last character through the line ending, an item's, a quote's, the CRLF
   twin, a blank line between, a table, a sub-item's fence, an indented block and a footnote reference ending the
   prose, with the start edge's bytes, a sub-item's opener, the blank line before an indented block and a point inside
   the reference as controls; an inner code line's trailing whitespace, tab and line feed in ten fences, the adjacent
   offset, the next line's first character, a point at a character, the last line and a line with no trailing
   whitespace as controls; and the unplaceable fence under a `fences` tokenizer override, its opener, the indent and
   the blank line before it, in an item and in a quote, a point inside the hole card-only, with no later fence, the
   later fence's own opener and marked's own fence as controls; and the review's closing pass: a formula alone or a
   picture alone on the line before a nested table or fence, an item's with and without a blank line, a picture, a
   display formula, a quote's, before a fence, a second item's after a text item, with the item's prose after the
   table, and a footnote reference alone, at every offset from the hole's end through the block's first character and
   inside the formula's TeX, card-only, with an item's prose then its formula then the table and a top-level formula
   paragraph then a top-level table as controls; and the PR review's round 1, the fifth test: under an outer item
   holding a formula alone, a sub-item's table's outer line feed, the sub-item's indent and marker and the table's
   first character card-only, with a blank line between too, the fence twin, and a list item's table in a quote
   holding a formula alone before the list, with an outer item's prose then a sub-item's table, a formula-alone item
   then a table item and a point inside the cell as the controls, and the fourth test's control that pinned the
   closing pass's placement re-pinned to the card; and the PR review's round 2, the sixth test: under an outer item
   whose text precedes a formula alone, a sub-item's table's points from the blank line after the text through the
   formula's bytes, the blank line, the sub-item's indent and marker and the table's first character card-only, the
   tight shape, the picture twin, the fence twin, the quote twin and the formula on the text's own line (that line's
   offsets after the text), and a formula-alone item then a table item placing before the first cell's text at the
   top level, nested in an item, in a quote and in a second item alike, with an outer item's text then a sub-item's
   table, with a blank line between too, an item's text holding the two items and a point inside the cell as the
   controls; with the Files pane's rows and undressed alike) holds the round 6 rules, the closing pass's and the PR
   review's rounds 1 and 2. Recorded by the review's round 6 and routed to a
   follow-up, no code change: a paragraph's trailing whitespace at a list item's end, past the first trailing space or
   at the line feed, places its point before the NEXT item's first character, in that item, where the Raw view keeps
   it on the item's row, identical on main 696229f84 and outside this slice's items (prose before prose; the adjacency
   rule's, `renderedSpot`), and the same offsets place so when an EMPTY fence, or a fence of one blank line, stands
   between that prose and the next item and ends the item, the fence having no positioned character for the
   line-before rule to stop at, so they fall to the same adjacency rule, identical on main 696229f84 (prose
   after such a fence in the same item takes the point instead, before its first character; the review's closing
   pass); a table's first character's point in a list item, with a display formula between the item's prose and the
   table, sits after the prose above the formula's box, the formula's hole having no character to stand between,
   identical on main 696229f84, whose hole rule placed it there too (the fix shape is the formula-span check the round
   3 record names); and the blank line before an indented block in a list item places its point before the block's
   first character, in its first row, round 5's rule that an indented block has no start edge, where main placed it
   after the item's text (the indent before the first line stays the line's either way). Recorded by the review's
   closing pass as a shape left to the same follow-up, then ruled and changed by the PR review's round 1: under an
   outer item holding a formula alone, a sub-item's table took the outer line's line feed and the sub-item's indent
   and marker into its first header cell, before its first character, where its first pipe sits by round 4's rule for
   a table that begins its item, the closing pass's rule leaving them since the table begins its own item, while main
   696229f84 kept the card on every one of them. Since the PR review's round 1 those bytes, and the table's first
   character with them, keep their card: `unpositionedBefore` reads the items and quotes enclosing the block's own,
   out to the block's node, so the outer item's formula is unpositioned content before the table, and before the fence
   twin (the ruling: a point places in a cell only where the placement is the cell's own text exactly, and the card,
   the refusal's side, is kept otherwise, an anchor carrying a character outside the cell being wrong in the unsafe
   direction); anchor-map-line-edge-points.test.ts's fifth test pins the shape card-only, red over a git archive of
   4a3e18664, the PR's reviewed head, with the point in the first header cell, and its fourth test's control that
   pinned the closing pass's placement is re-pinned to the card. The PR review's round 2 (over the head c4a225379)
   found round 1's reading stopping at an enclosing item as soon as that item held a positioned character before the
   block, so the shape's neighbour, an outer item whose text precedes a formula alone, then a sub-item's table, still
   took the formula's bytes, the blank lines and the sub-item's indent and marker into the first header cell (main
   placed them after the text, never in a cell), and counting an earlier sibling item's content when the list was
   nested in an item or a quote (the reading descended the nested list's element), so a formula-alone item followed
   by an item beginning with a table kept the card nested or quoted and placed before the first cell's text at the
   top level. Since round 2 the item holding the block's last positioned character before the offset is read for the
   content between that character and the block alone, another table or code block of the block's standing there
   being a block and not content (round 5's start edge), and a list element holding the block is never descended, a
   sibling item's content being no part of the rule at any nesting: the neighbour's points keep their card, and the
   sibling shape places alike at every nesting, before the first cell's text. The rule, stated in
   `unpositionedBefore`'s and `edgeSpot`'s docstrings: a placement never carries bytes from outside the block into a
   cell or a row, and the card is kept wherever the exact-position arithmetic would put them there.
   anchor-map-line-edge-points.test.ts's sixth test pins the neighbour (the loose and the tight shape, the picture,
   fence and quote twins, the formula on the text's own line) card-only and the sibling shape's placement at the top
   level, nested in an item, in a quote and in a second item, red over a git archive of c4a225379 in both, with the
   outer item's text then a sub-item's table, with a blank line between too, an item's text holding the two items,
   and the fifth test's controls unchanged.
   A Raw quote spanning the delimiter row paints the header cells and the body cell either side of the row that
   renders nothing, where Slice 5 pinned "paints nothing and the card keeps Reveal" (open question 5, the default: the
   quote covers those cells). The fallback needle's quirks the Slice 5 note left (a `*` opening in one cell and
   closing in another read as emphasis, a `>` lost at a quoted code line's start, a fence line's backticks dropped)
   bite only on the quotes the fallback still serves: a fence line's, the delimiter row's, a cell the per-cell
   fallback holds, a code block the placement could not read. The hole at a range's edge stays unpainted for the holes
   that remain (a formula's zero text, a footnote reference's number, a callout's title, the front matter); tables and
   code have left the rule's neighbourhood (open question 11, the default). anchor-map.test.ts (38, the fence's and
   the table's deletion points place, the html block's and the blank line's stay unplaced),
   anchor-map-rendered-points.test.ts (8, one new over a fenced block's points and the nested table's re-pin, one new
   for the table's end, the review's round 3, and two new in its round 4: a table or a fence that begins a list item,
   and a CRLF note's soft breaks and item endings outside code), anchor-map-boundary-points.test.ts (8, the cell's and
   the fence's bare deletions place, the html block's stays card-only), anchor-map-block-edges.test.ts (5, the nested
   fence's edge kept, now by the fence line's hole) and anchor-map-fallback-markup.test.ts (25, the delimiter-row
   quote's cells) hold it.
5. *Item 5, the display formula under a highlight takes a block class on its box* (open question 4, the default:
   built). A display formula is a block of its own line, which no inline mark can wrap (the pairing reads the root's
   children, and a mark between `.katex-display` and its `.katex` breaks KaTeX's layout), so a comment on `$$ ... $$`
   alone painted nothing in Rendered and its card offered Reveal. Now `paintRendered` stamps the covered formula's own
   `.katex-display` box (`displayBoxOf`) with the block class of the paint's first class token, `fc-hl-block` for
   `fc-hl` and for `fc-hl fc-hl-context`, `fc-presel-block` for `fc-presel`, plus every data attribute the paint sets
   on a mark, once, and returns the box among the marks in document order (`stampBlock`, `withBoxes`): a range from
   the prose before the formula into the prose after it returns the mark before, the box and the mark after; the
   formula alone returns the box where it returned null, so its card offers Scroll. `coveredFormulas` tests the hole's
   span as `formulaSpan` gives it, the opener, less any indent before it, through the closing `$$`, where a display
   formula's hole now ends (the mathBlock case of `walkBlocks`: the raw less the spaces and line feeds the tokenizer
   takes after the closer; the review's round 2: before, the hole ran to the raw's end, which inside a blockquote or a
   callout lay past the `> ` marker of the quote line after the formula, where `formulaSpan`'s whitespace trim back
   from the end stopped, so a quote that is exactly a quoted `$$` block, the opener through the closer, never covered
   its formula, no stamp and the card offering Reveal, and the Raw offer for a boundary in the formula preselected the
   markers of the lines after it; at the top level the two ends agreed once trimmed), so the exact quote covers the
   formula at the top level, in a list item, in a quote and in a callout; inline formulas are untouched. The block
   paint serves the two comment classes alone (`BLOCK_PAINT_FOR`, the mirror of file-comments.ts's
   `BLOCK_PAINT_CLASSES`, pinned as one set by tests/test_guide_files_cells_and_code_lines.py): a change's tint
   (`fc-ins`) stamps nothing, so a change across a display formula keeps its shape, the prose either side marked and
   the box bare, and a change on the formula alone stays on its card. The panel's half: `unwrapMarks` strips an
   element that is not a MARK in place (`stripBlockPaint`: the block classes the caller names, every one by default
   and, from `Panel.unpaint`, the ones its selector named; once `fc-hl-block` is gone, `fc-hl-context` and data-act,
   data-id, data-ids, data-new, tabindex, role and title go with it; the children untouched) instead of unwrapping it,
   which would hoist KaTeX's root into the page, so the pending target's three unpaints leave a highlight standing on
   a box the two paints share (the review round 1: Cancel over a highlighted formula had stripped both classes and
   every attribute, the box bare and no longer a control until the next full pass); the strip's removal of the box's
   tabindex blurs a box holding the keyboard (Chromium blurs at once an element a tabindex change makes unfocusable,
   and the attribute set again focuses nothing), so `refocusMark` stands down only while the held element is still the
   document's active element, not merely in the body, and gives the focus back to the box the pass stamps again, the
   same element, as it gives a mark's successor the focus (the review's round 4: a peer's comment landing by the
   panel's poll had left the keyboard on the body, Enter opening nothing, while the box kept its Tab stop);
   `paintAll`'s unpaint and the pending target's three unpaints select the block classes beside the marks';
   `lineBoxOf` answers a stamped box as its own line box, a display block stopping the climb at itself; `goTo`'s
   fallback selector finds the box; the pass adds `fc-hl-context` to a stamped box itself in the context state (the
   paint stamps the first token alone, and the pin in tools/file-review-plan-anchors-states.test.mjs on the marks' own
   context line stands). Both sheets, byte-equal: `.fileview-md .katex-display.fc-hl-block` (the highlight's wash and
   ring, cursor, no padding, so the box keeps its size), the same head with `.fc-hl-context` (the ring dropped for the
   dashed outline), `.fileview-md .katex-display.fc-presel-block` (the accent); the arrivals dot rule names the block
   class and the print strip names it and its `[data-new]` form (the review's round 3: the dot's rule, four selectors
   deep, outranked the strip's bare block class, so a box whose comment arrived unseen printed its dot while every
   mark printed bare; the added selector has the dot rule's weight and stands later in the sheet, byte-equal in both
   sheets); the three heads join fileview-parity's RULES. The trim never measures the box (`isBlankMark` requires a
   MARK) and the pairing's blank-mark read is MARK-only, so the class changes nothing about the block table. Two
   comments on one display formula share one box, so the pass keeps the covering set on it: `data-ids` lists every
   covering comment's id in the pass's order and `data-id` names the last, the one in front, as the innermost mark is
   under an inline overlap (file-comments.ts `coverBox`, after each paint that returns the box, in `paintAll` and
   `repaintPreselPass`); `ownMarks` reads a box by either attribute, so each card's Scroll finds it, `goTo`'s fallback
   selector adds `.fc-hl-block[data-ids]`, `openCovering` opens every card the set names on a click, and the arrivals'
   dot on a shared box stands while any covering comment is new (`reflectSeen`, which keeps a stamped box's `data-new`
   while another covering comment is unseen; pinned by the PR review's round 1, before which a `reflectSeen` dropping
   `data-new` unconditionally left every suite green: two comments on one formula, one of them seen, the box keeps
   `data-new` and loses it once the second is seen, file-comments-block-paint.test.ts with the stand-in's rects
   placing one card on screen and the other below the fold, and file-comments-block-paint-seen-browser.test.ts over
   the real margin layout, the cards' track scrolled so the later card lies outside its box); the review
   round 1: before, the later
   paint's id overwrote the earlier's, a click opened one card and the earlier card's Scroll fell to Reveal. Left as
   limits: the fill's two other display shapes, a top-level `span.katex-error` for TeX KaTeX could not parse and the
   belt's `code.md-math-src` inside a `pre` for a formula past the size bound, have no sheet rule and are not stamped
   (the brief's item 5 names the `.katex-display` box alone), so a paint over such a formula alone still returns null
   and its card offers Reveal, as before this slice; a nested display formula's stamped box reaches `lineBoxOf` in the
   browser legs through one read alone, the pending target's standing box read in `repaintPreselPass` at Cancel (the
   sixth leg's quoted formula, the review's round 2; the top-level legs' Cancel drives the same read; the view
   switch's paint reads no line box, and no leg of the file opens the composer in Rendered over a span holding a
   formula, the repaint's other read of a box), and no leg asserts the repaint's scope from the own-box answer, which
   would take a highlight standing in the quote beside the formula (none is served); the answer is pinned by source
   text in file-comments-block-paint.test.ts. anchor-map-obsidian.test.ts (the display-formula pin re-pinned, the box
   stamped and returned between the marks, and one new test over the item's shapes: the formula alone with and without
   the raw's line feeds, `fc-presel-block`, a two-token class, a second paint stamping once, the trim keeping the box,
   `fc-ins` stamping nothing, an inline formula still under a mark, the flag and the belt bare; and a second new test,
   the review's round 2: a quoted `$$` block with a blank `>` line then a tail, the tail directly after the closer, in
   a callout's body, last in its quote, at the top level and in a list item, the exact quote stamping the box alone,
   from the row's start too, on into the tail returning the box then the tail's mark, and the Raw offer for a boundary
   inside the glyphs preselecting the block through its closing `$$` with no marker after it; and a third new test,
   the review's round 3: a record pin holding the paint test's comment to the code, the mathBlock hole's end at the
   closing `$$`, witnessed by the Raw offer for a boundary inside a quoted formula's glyphs with a quote line after
   the closer and inside the fixture's top-level formula, and no comment in the file saying the hole's end lies past
   the raw's trailing line feeds), file-comments-block-paint.test.ts (10, new: the pass strips a stamped box in place
   and unwraps the marks beside it, `unwrapMarks` over a mixed list, the sheets' rules by token with no padding, the
   print and arrivals rules, the print strip's pin re-aimed at the `[data-new]` form in the review's round 3, the
   readers by source text; two served comments' box painted by the real pass, a click opening both cards and each
   card's Scroll finding the box; the strip by class leaving a highlight's stamp under a stripped target; the box
   holding the keyboard across a status landing refocused, the same element, Enter opening its card, the stand-in
   modelling the engine's blur on a tabindex removal, the review's round 4; and the PR review's round 1: the shared
   box's `data-new` kept while one of two covering comments is unseen, the earlier card and the paragraph's on screen
   and the later card below the fold, and gone once the later card is seen, the press bookkeeping's other ends, and a
   repaint during a press, the release focusing the successor), file-comments-block-paint-seen-browser.test.ts (1 leg,
   new, the PR review's round 1: over the real viewer and panel at pane 900, two comments of the session's on the
   formula and one on the paragraph above arriving after the open, the track scrolled so the later formula card's top
   sits at the box's bottom edge, a real click marking the two inside seen and the box keeping `data-new`, the track
   scrolled on and a second click taking the dot off the box) and
   md-config-math-block-paint-browser.test.ts (8 legs, new: a served comment on `$$ ... $$` at pane 900 and 380 and in
   the chat modal shows the wash with tabindex, role and title set, the KaTeX child intact and no top-level mark, a
   click on the glyphs opens the card with Scroll and no Reveal, print strips, a reload re-stamps once; the Raw-made
   pending target carried into Rendered wears `fc-presel-block` with no mark and Cancel leaves no class or attribute;
   the dress on a hand-stamped box at no change of size and a same-body repaint stripping it; two comments on the
   formula at pane 900 and in the chat modal, the set and the front on the box, a click opening both cards, the
   earlier card's Scroll staying in Rendered and a reload rebuilding the set; the pending target over a highlighted
   formula, Cancel leaving the highlight with its data, its control attributes, its wash and ring; a display formula
   inside a blockquote with a blank `>` line and a quote line after its closer at pane 900, a served comment whose
   quote is the quoted block, the opener through the closing `$$`, stamping the quote's box with its data and control
   attributes, wash and ring, a click on the glyphs opening its card with Scroll and no Reveal, then a real Raw drag
   over the three `> $$` rows whose pending target the switch to Rendered carries onto the box as `fc-presel-block`,
   Cancel leaving it bare; a comment of the session's on the formula arriving after the open, beside one on the
   paragraph after it, at pane 900 and in the chat modal, the dot on the stamped box on screen as on the mark, off
   under print media with the wash and ring while the attributes stand, and back on screen, the review's round 3; the
   keyboard on the box across a peer's comment landing by the poll, at pane 900 and in the chat modal, Tab from the
   paragraph's mark to the box and a click on the glyphs, the box the same element and the document's active element
   after the landing, Enter opening the card, the engine's blur on a tabindex removal measured in the page, the
   review's round 4) hold it, with file-comments-changes.test.ts's unpaint-order pin and
   file-comments-reply-review2.test.ts's `goTo` selector pin re-aimed at the widened selectors.
6. *Item 6, the records, and what the earlier slices routed here.* docs/guide.md's Comments paragraph: a sentence
   before the refusal sentence says a table cell and a line of a code block can be commented from the Rendered view
   like any passage, the parenthetical "(a table, a code block)" becomes "(a selection across two cells of a table, a
   formula)" (open question 7, the default), and one clause says a comment on a formula that stands on its own line
   highlights the whole formula; the refusal's tail clause the vocabulary and Slice 5 pins read stands byte for byte;
   tests/test_guide_files_cells_and_code_lines.py (8, new) pins the three clauses flattened and each against the
   source that keeps it. The comments in code that stated the old boundary are reworded: anchor-map.ts's header (the
   Rendered bullet now says cells and lines are positioned as prose is, HTML, entity-bearing prose and escaped link
   labels keeping the refuse-by-design sentence), the code-lines paragraph (the mapping reads no row; the two helpers
   deleted), `blockLexView`'s docstring, the formula-obstacle example and the fallback's ordinal motivation; a grep
   over ui/webview finds no comment saying a cell or a code line refuses from Rendered outside history notes (the
   review's round 3 found one present-tense paragraph in `mapRenderedSelection`'s obstacle pass still listing a cell
   as a hole and a cell-to-html-block drag as refused as touching the table, and the obsidian test's first-obstacle
   title saying the same; both reworded); code-block.ts's "Slice 8's mapping" sentence was already reworded by Slice
   5's review, so nothing changed there; one comment clause in reader-place.ts that named `codeLineAt` says "(one row
   per line)"; the docstring example in file-comments.ts of a refusal the mapping gives for a reason of its own
   (deletionUnder's) names a selection spanning two cells of a table, the everyday reason since this slice, where it
   named a table. CONTEXT.md is unchanged: the build coined no term. The store guards, green before by design and
   titled so: tools/file-comments-host-anchors.test.mjs (15, one new: a cell holding `\|` located byte for byte by
   `uniqueAnchor` and `locateExact`, the comment verb storing the slice with both escapes and `anchorAt`, the two-line
   tab quote beside it) and tests/test_file_comments_e2e.py (27, two new, through the real dispatcher and the real
   host: the `\|` cell with and without a position and its inner code span alone; the two-line quote with `\n\t`
   inside it as bytes, and the snapped one-line quote starting after the tab). The ledger entry is
   upstream/2026-09-12-markdown-viewer-slice8.md (tier feature). Routed here and decided: the Slice 2 record's
   "paragraph half of the line rule waits on Slice 8's inline map" (slice2-build.md) is corrected, not built: the
   plan's Slice 8 text names tables and code only, and the caret-to-offset mapping the record wanted exists already as
   `descend` and the positioned `pos`, without an export for the reader's place, which a follow-up could add (open
   question 12, the default); a raw HTML `<table>` stays an html block, refused by design (the Slice 5
   note's not-modelled list); the formatting element a paragraph leaves open (`<b>`, `<i>`, `<a>`, `<code>`, `<em>`
   with no closer), routed here by the Slice 5 review's round 4 with its `Block.leaves` fix shape, is NOT built in
   this slice and stays open with that shape (the brief records it under its section 2 and routes it to no unit; the
   pairing was not touched by the build, whose items are the walk and the paint; built since as decision 52 of
   plans/file-review.md, 2026-09-18, by a rule the viewer and the map share rather than by `Block.leaves`: an inline
   start tag with no end tag in its block renders as its own characters on both sides, so the block maps and that
   fix shape is moot for the bare spelling, while the self-closing spelling (`<b/>`, `<div/>`, `<table/>`,
   `<title/>`) stays HTML and keeps that shape, as decision 52 records); the 1,000-row table's numbers the
   brief asked for were taken beside the fence's (item 2), the table's emission running once per source on the Walked
   row as before and the one-cell rule's check being one scan of the table's cells per selection. Five sentences in
   earlier notes are history since this build: the Slice 5 note's guarantees paragraph (above) says "PRE and TD stay
   refused, so the fallback's ordinal keeps marking the changed cell or line under the raw needle and the pipe rule"
   and "Slice 8's boundary stands", which items 1, 2 and 4 replace with the exact path, the fallback's ordinal serving
   the unpositioned alone (the PR review's round 1; that paragraph now says so); the Slice 5 note's item 10 (i) says
   "Slice 8's boundary stands: a cell or a code line
   selected from Rendered refuses with the Raw offer and the switch preselects the passage, a selection across two
   cells refuses with no preselect", where items 1 and 2 map the cell and the line and item 3 refuses the two-cell
   selection with the Raw view preselecting the span (the review's round 2; that clause now says so); the Slice 3
   note's item 9 says `codeLineAt` and `codeLineStart` "stay, exported for Slice 8's exact code-line mapping", where
   item 2 deleted them (the sentence there now says so); and the same item's account of
   anchor-map-wrapped-code-browser.test.ts ended "a Rendered selection inside code is still refused with the Raw
   offer", where the leg's step 7 now asserts the mapping to the word's own offsets (that sentence now says so too);
   and the Slice 5 note's item 5 says the Raw offer at a display formula is the hole's span with the line feeds the
   block's raw carries after its closing `$$` trimmed, where since the review's round 2 the hole itself ends at the
   closer and only an indent before the opener is trimmed (item 5; that sentence now says so). The review's round 1
   left item 2's count of anchor-map-code-lines.test.ts at 14 and item 5's of
   md-config-math-block-paint-browser.test.ts at 3 legs where its list said 15 and 5 (its round 2 corrected both);
   tests/test_markdown_viewer_plan_note_counts.py (5, new) holds each note's two counts of a file, the item's and the
   list's, to each other, so the record cannot contradict itself that way unseen. The review's round 2 moved the
   display formula's hole end to the closer and left the paint test's comment in anchor-map-obsidian.test.ts saying
   the hole's end lies past the raw's trailing line feeds; its round 3 reworded the comment, and the file's
   thirty-first test holds it to the code. Found by the review's round 2 and routed to the next edit of those notes,
   not this slice's: twelve lines of this plan outside this note run past the 118 columns the build notes wrap at (one
   line of the Medium defects at 168, two of the Slice 3 note at 121 and 119, one of the Slice 4 note and eight of the
   Slice 5 note at 119), identical on main 696229f84; this note has none, so a width check over the whole plan flags
   lines no item of this slice wrote. Tests, by file (every new node test on the shim's stand-ins with `hideEdges`;
   every browser leg over headless Chromium and the real bundles, 0 skipped, counted on every run): anchor-map-cells
   (18, new; `tableHole` reached under a table tokenizer override, the PR review's round 1), anchor-map-cells-browser
   (6 legs, new, the sixth the review's round 5), anchor-map-cells-formulas (6,
   new: the review's rounds 4 and 5), anchor-map-block-edge-points (7, new: the review's round 5; the closer's own
   line feed, the PR review's round 1),
   anchor-map-line-edge-points (6, new: the review's round 6, its closing pass and the PR review's rounds 1 and 2),
   anchor-map-code-lines (16, new; since the PR review's round 1 its header scopes the fails-before claim to the cases
   that map a code character and names the eighth, the empty fence, as the exception, a guard green before the slice),
   anchor-map-code-lines-browser (5 legs, new), anchor-map-blank-fence-points (6, new), anchor-map (38, six re-pinned
   and one re-titled), anchor-map-obsidian (31, four re-pinned, three new and the first-obstacle test re-titled),
   anchor-map-wrappers (38, six re-pinned), anchor-map-fallback-markup (25, one re-pinned and the code cases
   re-titled), anchor-map-rendered-points (8, one re-pinned and four new, the blank line's pin worded as the fallback
   over its undressed pre, the first test extended with the top-level table's first character, the second new test the
   table's end, the third and fourth the review's round 4: a table or a fence that begins a list item, and a CRLF
   note's endings outside code), anchor-map-boundary-points (8, two re-pinned), anchor-map-block-edges (5, re-titled),
   anchor-map-change-marks (7, two re-titled with new pins and one extended), anchor-map-wrapped-code (4, two cases
   deleted and the pin re-aimed), anchor-map-wrapped-code-browser (1 leg, step 7 re-pinned),
   file-view-copy-map-browser (2 legs, re-pinned), file-comments-block-paint (10, new, the print strip's pin re-aimed;
   the shared box's `data-new`, the press bookkeeping's other ends and the pressed mark's successor, the PR review's
   round 1), file-comments-block-paint-seen-browser (1 leg, new: the PR review's round 1),
   md-config-math-block-paint-browser (8 legs, new), styles-fc-hl-code-row-browser (1 leg, new),
   file-comments-mark-first-glyph-drag-browser (2 legs, new: a real drag begun on the leading half of a highlight's
   first glyph selects the passage and offers Comment with no card opened, in a paragraph, on a nest of two marks and
   in a fence row; the review's round 3; the second leg the press bookkeeping's other
   ends, a blur, a context menu and a second press with no release between, the PR review's round 1), fileview-parity
   (four heads), file-comments-margin-review (18, the
   `ownMarks` pin re-aimed at the covering-set selector), file-comments-changes (23, one re-pinned),
   file-comments-reply-review2 (9, one re-aimed), file-comments-inline-review (7, one re-pinned: the card-only
   deletion moved to a fence's opener line, a zero-text hole, and the code line's deletion asserted struck in its
   row), styles-fc-arrivals-line-fit (14, the dot head's pin re-aimed at its fourth selector, the stamped display
   formula), md-config-paint-trim-browser (5 legs, its own unpaint helper stripping a stamped box in place, a guard on
   the harness, green before), the fixture anchor-map-fixtures/cells.md (new);
   tools/file-comments-host-anchors.test.mjs (15, one new), tests/test_file_comments_e2e.py (27, two new),
   tests/test_guide_files_cells_and_code_lines.py (8, new; one pin re-aimed at the shared `ONE_CELL` constant and its
   two refusals in the review's round 3, and at the round 4 offers, the pass's widened by a covered formula of the
   same table and the covered formula's the table's covered cells' span, and in round 5 at the one rule both read,
   `cellsRule`, counting the cells by source span), tests/test_file_review_plan_boundary_points.py (12, two re-aimed
   with plans/file-review.md's follow-on note clause and its Tests bullet, which say the deletion inside a fence or a
   cell, card-only before, places since this slice), tests/test_markdown_viewer_plan_note_counts.py (5, new). Every
   case that changes behaviour fails over a `git archive` of 6020e9309 (the head the branch was cut from; the base
   since the rebases, 929ae86e1, differs from it in this plan and in reader-place.ts among the files the slice
   touches) and, where the file bundles there, of the fork's main at the build, 213fde5fa, the review round 1's over
   one of 7201d7954 (the build's head as it stands on the branch; its earlier shas, and each commit's below, are in
   the mapping at the head of this note), the review round 2's over one of 499ec377f (round 1's fix commit), the
   review round 3's over one of e2cd869cb (round 2's fix commit), the review round 4's over one of 2dba77427 (round
   3's fix commit), the review round 5's over one of 473307626 (round 4's fix commit), the review round 6's over one
   of 5d9e4ae43 (round 5's fix commit), the review's closing pass's over one of 3b6950074 (round 6's fix commit), the
   PR review's round 1's over one of 4a3e18664 (the PR's reviewed head), and says how in its commit; the guards say
   they are guards.
   The guarantees the families re-verify: highlights are measured `<mark class="fc-hl">` elements over the range's
   text nodes with their data-act, id, tabIndex, role and title, the margin layout reading their boxes, plus one
   element that is not a mark, the stamped `.katex-display` box, which the panel records among its marks, strips in
   place of the block classes the caller names and never unwraps, `data-ids` on it when several comments cover the
   formula; the pairing is the one table the reader's place, the change marks and the selection map read, and every
   table's and fence's `chars` are byte for byte what they were, so the `<table>` and the `<pre>` pair as before at
   every depth; a cell's or a line's mark stands by the source's position, so the right occurrence is the selected
   one, and the fallback's ordinal under the count guard serves the unpositioned alone; the float, the composer and
   the save keep their rules and the composer's quote stays the exact source slice, an escaped pipe and a tab reaching
   the store as bytes; and the Raw view is untouched.

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

## Fix: the gate before adoption (2026-09-20)

Until this fix the viewer's figure gate did not hold: WebKit requested an HTML img on an unlisted host while the gate's
placeholder stood, and WebKit and Firefox requested an inline svg's image. The review of the link-navigation follow-on
found the img hole on main (fork PR 862, round 1, finding extra8-3; two refuters confirmed it with real servers); the
review of this fix found the svg vectors at the base (round 1, a finder and three refuters, each with its own servers).
The fix is its own branch, a fix-tier PR and a privacy surface, so it lands on the owner's word.

**The hole.** Under WebKit a figure on an unlisted host was requested while the gate's placeholder, "Image from <host>.
Click to load.", stood, so the placeholder was a false assurance. `mdBlock` (file-view.ts) adopted the sanitized nodes
into its live-document box first (`box.replaceChildren(...Array.from(sanitizeMd(dirty, mintHeadingIds).childNodes))`)
and ran the figure chain after: resolveFigureRefs for a URL document, rewriteFigureSrcs for a file, gateRemoteFigures
for both. WebKit starts an img's fetch synchronously when the element's node document becomes one with a render tree;
the adoption is enough, a place in the tree is not needed. A figure of the file's own folder was requested against the
page, as the attribute read before rewriteFigureSrcs repointed it, and then again through /file. In Chromium and Firefox
the servers' logs held no line for either of those img figures before the chain ran, so for an HTML img only WebKit
leaked; the engines' scheduling of the fetch was not instrumented, the logs were read. For an inline svg's `<image>` the
gate held in Chromium alone. Firefox requested a gated svg image, spelt `href` or `xlink:href`, while its placeholder
stood when the chain's work between the adoption and the gate's strip of that element was long: over the second leg's
note (3000 paragraphs with a link each, then the two svg images) both figures in 3 of 3 runs at the base, over 400 plain
paragraphs in 1 of 3; the run counts per note are under "Run counts, the svg vectors" below. WebKit requested the
`xlink:href` spelling in every run and the `href` spelling in none.

**The fix.** `sanitizeMd` (md-sanitize.ts) returns the body of DOMPurify's own parse document (RETURN_DOM; DOMPurify
parses the markup with DOMParser, or into `implementation.createDocument` when that fails), a document with no browsing
context, whose `defaultView` is null, in which nothing loads. The whole figure chain now runs over that body and the
adoption comes after: `const clean = sanitizeMd(dirty, mintHeadingIds)`, then resolveFigureRefs, rewriteFigureSrcs and
gateRemoteFigures over `clean`, then `box.replaceChildren(...Array.from(clean.childNodes))`. The rule: every pass of
mdBlock that sets, repoints, moves or creates a fetching element runs before the adoption. Every pass that writes a
fetching attribute is in that chain, the fold of an svg image's `xlink:href` into `href` (rewriteFigureSrcs for a file,
resolveFigureRefs for a URL document) and the gate's move of either spelling aside (figure-gate.ts) included; the fence
pass, the one pass that re-parses markup (code-block.ts wrapCodeLines serializes each code element through innerHTML and
parses it back), runs on `clean` before the chain since the fork PR's round-2 push (the branch's fourth round,
2026-09-20), so the chain judges the elements the re-parse creates (the fence hole, below). The URL document's link
resolution, which sat between resolveFigureRefs and the gate, stays after the adoption; no pass after the adoption sets,
repoints or moves a fetching attribute, and none re-parses markup. The rule's domain is mdBlock. The hooks renderBody
runs after mdBlock returns (folds.restore and restoreHeldFolds, stampBodyWidth, syncOutline, the onRendered hooks, among
them the Comments panel's regions layer, which wraps each of the box's imgs in a `span.fc-imgwrap` while the panel is
open (file-comments-regions.ts), and armFigureLabels, which puts a label beside a figure that failed to load, and the
text-size stamp `data-fv-text`) wrap, move or label elements the chain has already judged, inside the live document, and
set no fetching attribute. A move is one of an img's relevant mutations in the HTML specification (its insertion and
moving steps re-run the update of the image data), and what that update reads is the element's own `src` and `srcset`: a
gated element carries neither (its source is under `data-fv-gated-*`), and an ungated one carries what the chain left
it, an allowed host's URL or the /file route, so a move after mdBlock can request only what the chain allowed. Those
hooks are judged by read of the code, in the fork PR review's pre-answer record (its section 1, "Same paint after
mdBlock returns"), not by a measurement. The chat's `md()` path stays ungated by the recorded ruling; the same order
applies to any sanitizeMd caller that adopts nodes.

**The instrument.** The claim is about bytes leaving, so the test reads real servers' request logs, never page.route
or context.route, which answer a request inside the browser and can report one the network never carried or miss one
the engine issued before the route saw it. file-view-figures-gate-adopt-browser.test.ts runs three servers on
127.0.0.1: a figure server for `remote.test`; a harness server for `romp.test` that serves the pane page, the Files
bundle, the notes and a folder figure through /file, with the kernel's Referrer-Policy header on every response; and
an HTTP forward proxy that logs every request the browser hands it and forwards by hostname. Each engine is launched
with that proxy, so the browser fetches under the unlisted name without DNS and every request is logged twice, by the
proxy and by the server it reaches; after each open a drain makes one sentinel round trip through the proxy and waits
250 ms. Its three scenes: a note with a figure on the unlisted host; a note with a figure of its own folder; a
document opened from its URL, at /notes/note.md on the harness, with a figure of its own folder, one on the unlisted
host and a protocol-relative `<img src="//remote.test/proto.png">`. The second leg,
file-view-figures-gate-adopt-svg-browser.test.ts, is the same instrument with one figure server answering for two
unlisted hosts, `remote.test` and `other.test`, and one scene: the 3000-paragraph note with an svg image spelt `href`
on the first host and one spelt `xlink:href` on the second, clicked one at a time.

**Measured.** In Playwright's Chromium, Firefox and WebKit, at the base 2d41e5c9b and after the fix. At the base,
WebKit: the figure server logged `GET /fig.png` under Host `remote.test` while the placeholder stood, and the harness
logged a page-relative `GET /fig.png` for the folder figure beside the request through /file; for the URL document the
figure server logged `GET /fig.png` and `GET /proto.png` under Host `remote.test` while both placeholders stood, and the
harness a page-relative `GET /rel.png` before `GET /notes/rel.png`; Chromium and Firefox: no such line in any of the
three scenes. The second leg, copied to the base: Firefox, both svg figures requested while their placeholders stood;
WebKit, the `xlink:href` figure requested, the `href` one not; Chromium, no line for either. After the fix, in all three
engines: no line for a gated figure until its click, which makes exactly one request, `GET /fig.png` under Host
`remote.test` with no Referer; for the svg figures, `GET /drawing-href.png` under Host `remote.test` and
`GET /drawing-xlink.png` under Host `other.test`, one per click, the other figure unrequested between the clicks. The
folder figure is requested once, through /file, and never as `/fig.png`; the URL document's folder figure once, as
`/notes/rel.png`, and never as `/rel.png`. The premise, executed over the real sanitizeMd in each engine: its body's
ownerDocument is another document with `defaultView` null and an img in it fetches nothing, where an img of the live
document with a src and no place in the tree fetches in every engine, the control that the instrument sees a fetch the
page does make.

**Run counts, the svg vectors.** Every count is at the base 2d41e5c9b, 2026-09-20, a request counted only while the
placeholder stood, read from real servers' logs through a logging proxy; the numbers are the review's records, brought
together here (the round-1 fixer's runs for the leg and its sizing variants, the round-1 finder's and the three
refuters' for the rest), and this paragraph is the one place they are stated, the other records pointing here. The
second leg, in its three runs: Firefox both figures 3 of 3, WebKit the `xlink:href` figure 3 of 3 and the `href` one 0
of 3, Chromium 0 of 3; a sizing variant of the same note, Firefox alone: the `href` figure 3 of 3. The leg over shorter
notes, Firefox alone unless said: 400 plain paragraphs 1 of 3 (the `xlink:href` figure; WebKit 3 of 3 `xlink:href` and
Chromium 0 of 3 in those runs), 2000 plain 1 of 3 (the `href` figure), 400 with a link, code and emphasis each 1 of 3
(the `xlink:href` figure), 400 plain with forty gated svg figures on a third host before the two 0 of 3. The review's
finder and three refuters (two reviewing the PR body draft, one reviewing file-view.ts), each with its own servers and
proxy, Firefox: one svg image spelt `href` followed by 300 gated img figures 4 of 5; the same image alone 0 of 6 and 0
of 4; beside one img figure 0 of 5, 0 of 5 and 0 of 6; the same image followed by 50 gated img figures 0 of 4; the
`xlink:href` image alone 0 of 4 and beside one img figure 0 of 4; in a note of about two dozen figure vectors 3 of 3
(the finder); in a five-figure note (an img, the svg image in both spellings, a folder svg image and a folder img) the
`href` image 1 of 7 and the `xlink:href` image 2 of 7 (a refuter); the last of two or three svg images in a short note
2 of 3, 3 of 5 and 1 of 5. WebKit, the refuters: `xlink:href` 4 of 4, 4 of 4 and 3 of 3; `href` 0 of 4, 0 of 4, 0 of 3
and 0 of 3. Chromium: no svg figure requested in any run by any instrument. After the fix, no request in any engine in
any run: the leg once per engine at the fix and once per engine in each later run of it (the review's sweep and the
head runs); the refuters 18 of 18, then 4, 4 and 2 runs, then 3 per engine.

**The fence hole.** Found by the fork PR's review and closed in its round-2 push (the branch's fourth round,
2026-09-20), on main and open at this fix as filed: mdBlock's fence pass ran after the adoption, over the live box,
and re-parsed every `pre code` subtree (code-block.ts wrapCodeLines, `code.innerHTML =
wrapLinesHtml(code.innerHTML)`), whose line splitter carries only `<span>` tags across a newline. An author's raw
multi-line fence in a plain (unnamed) code block, `<pre><code><svg>` / `<image src="http://<unlisted host>/x.png"/>` /
`</svg></code></pre>`, survives the sanitizer (`image` is in DOMPurify's svg tag list; `src` and `srcset` are in its
attribute list), and the chain never judges `src` or `srcset` on an svg image (figure-gate.ts FETCH_ATTRS.image is
`href` and `xlink:href`), so at the adoption nothing loaded; the re-parse then closed the `<svg>` at the line's end
and parsed the `<image>` in body, where the HTML parser makes it an HTML `<img>`, and its `src` or `srcset` fetched
from the unlisted host with no click. Measured 2026-09-20 with the fence pass after the adoption, over three such
fences (an image with `src`; a gated svg's image with `src` beside its `href`; an image with `srcset`), in
Playwright's Chromium, Firefox and WebKit: the figure server logged `GET /a-src.png`, `GET /b-src.png` and `GET
/c-set.png` under Host `remote.test` in every engine, by the review's probe first and then by the fourth scene of
file-view-figures-gate-adopt-browser.test.ts copied into a scratch copy of that head. Controls, clean: the same svg
outside a fence, on one line inside a fence, and a `<template><img>` (the review's probe, Chromium), and in a
`language-js` fence, which hljs escapes to text (the scene's control, all three engines). A side effect of the same
order: the line splitter counted the gate's own `<span class="fv-gate">` as an open span and repeated it as every
following line's prefix, so one gated svg image yielded three placeholders. Closed by the move: the fence pass runs on
`clean` directly after the sanitize and before the chain, so the chain judges the img the re-parse created and gates
it like any other; the same scene at the moved head, in all three engines: no line for the unlisted host, each of the
three fences holding one HTML img under exactly one placeholder with its `src` or `srcset` under `data-fv-gated-*` and
no svg image left, the control holding no img, and one click on a placeholder loading the host, one request per img,
no Referer. The three-placeholder effect is closed by the same move (one placeholder per fence in the scene's
assertion). The same move corrected a second product of the re-parse, measured 2026-09-20 in Playwright's three
engines by the fork PR review's verification (a note with an svg anchor on one line inside such a fence and one split
across lines, at the moved head and at a copy with the fence pass moved back after the adoption): an svg anchor split
across lines is re-parsed in body as an HTML `a` whose `xlink:href` is a plain attribute with no namespace. Under the
old order that anchor was followable (a section link, fv-frag) for exactly the reason the image leaked: the re-parse
ran after the passes, so its product carried what they had stamped on the element they judged (the post-adoption
fold's `href="#top"` and the link pass's class, copied into the HTML `a` the re-parse made) and escaped their
judgment, as the img it made carried a `src` the chain never read. With the re-parse before the passes, they judge its
product: the img is gated, and the split anchor, an HTML `a` with no `href` that still carries the plain `xlink:href`
(the fold's `a[*|href]` is a namespaced match and does not select it, so no `href` is written on it), is marked dead
(fv-dead, the title saying why) by linkMarkdownAnchors (file-view-links.ts) whether or not the author gave it an `id`
or a `name`. The mark is keyed on that attribute (the fork PR review's round 2, findings correctness-2, extra7-1 and
tests-4, 2026-09-20): the module exempts an href-less anchor target (an author's `name` or `id`, never a link) from
the dead dressing, and the split anchor with an author's id sat in that exemption, unclassed and untitled, painted in
the link ink by the sheet's bare `.fileview-md a` rule and doing nothing on a click, a silent dead link in all three
engines where this record had said a visible one; the exemption for a target carrying no `xlink:href` is unchanged,
since narrowing it generally would re-mark every author-written anchor target in every document. The key is the
attribute and not the fence, so one more anchor population is marked with it: an author's HTML `a` spelled with
`xlink:href` in the prose, which the sanitizer keeps with that attribute as a plain one and no `href`, never followed
and read as live in the same way, and is dressed dead too (the fork PR review's pre-landing verification measured it
in the three engines, and the two pins below hold it). Pinned in file-view-links.test.ts (the split anchor with an id,
with a name and with neither marked, the prose anchor spelled with `xlink:href` marked, the exempt target unmarked)
and in the sixth case of file-view-figures-gate-adopt-browser.test.ts (the id-bearing and the bare split anchor and
the prose anchor spelled with `xlink:href` fv-dead with the title and the sheet's help cursor, the prose's anchor
target unmarked, in the three engines; red for the id-bearing one at the head before the mark, no class and no title,
green with it). Closing the leak and making that anchor inert are one effect, a correction and not a cost: a link
inside a code fence stopped being live and says so, which is what every other link inside a fenced code block already
does, since the fence shows its markup as text. Behaviour, not privacy: an HTML `a` with no `href` follows and fetches
nothing. An svg anchor on one line keeps its namespace and folds as before, and an HTML anchor written as raw markup
in such a `<pre><code>` block is an element the passes read, not text, and is stamped the same under both orders (the
same probe: a path link, live at both heads). Predating this fix and outside it: an anchor whose `href` the sanitizer
stripped and that carries an author's `id` with no residue of the link stays exempt and silent, and the sheet's bare
`a` rule painting every href-less anchor in the link ink is general and untouched here.

**The re-parse population.** The rule needs every write that re-parses or re-serializes markup after the adoption
enumerated, a different grep from the walk of attribute writes. The verbs are the HTML-parsing entry points an element
or a document offers (innerHTML and outerHTML, matched bare, so a read or a write under any spelling;
insertAdjacentHTML, createContextualFragment, DOMParser, document.write; setHTMLUnsafe and parseHTMLUnsafe, which the
installed DOM typings, lib.dom.d.ts, carry; setHTML, the Sanitizer API's, which they do not yet), insertAdjacentElement,
and a template element, whose content is parsed markup. Derived 2026-09-21, at the head of the file review's landing
round's fixes, and again by the author's closing pass after the file review's landing round, which widened the seam
test's RE_PARSE to this command's template alternatives (it had matched a name under a quote alone; the same lines at
that head), over comment-stripped code by `grep -nE
'\b(?:innerHTML|outerHTML)\b|insertAdjacentHTML|createContextualFragment|DOMParser|document\.write\b|insertAdjacentElement|\bsetHTML\w*\s*\(|parseHTMLUnsafe|createElement\(\s*[^)]*template|\bel\(\s*[^)]*template'`
over mdBlock's region after the adoption line and over every module a pass in that region reaches, walked in three
steps: the identifiers called there (`keepVideoShape`, `linkHref`, `resolveDocRelative`, `linkMarkdownAnchors`,
`addFigureControls` and `linkifyFileText`; `addFigureControls` is the trail and figure-control follow-on's pass), each
resolved through file-view.ts's imports to md-links.ts or file-view-links.ts or to a local function; the local functions
those reach, transitively over bare calls (the figure control's decision among them), and every imported function a
reached local calls, resolved the same way (`parseSrcset` from figure-gate.ts, `figurePath` from
file-comments-model.ts and `pictureDest` from file-comments.ts, the figure controls' reads, filled here from the seam
test's IMPORTED_CALLEES; until the landing round the walk followed a reached local's local calls alone, so those three
modules sat outside the judged set while this paragraph stated a conclusion over a set it had not walked, and a live
re-parse write planted in any of them left the seam test green); then every
module those name in an import the compiler parses (an import declaration under any clause, an export with a
specifier, an import-equals, and a require() or import() of a string literal), transitively, under any quote and any
line break, a type-only import and a path outside ui/webview included, a specifier that is not a string literal
refused with its line, so file-view.ts itself re-enters through file-comments.ts's type import of the
viewer's action type and brings every module it imports along: forty-six modules
(../../vendor/track-changents/engine.js, actions.ts, anchor-map.ts, backend-names.ts, capped-read.ts, card-layout.ts,
code-block.ts, commands.ts, comments.ts, ctx-color.ts, docreview.ts, fence-source.ts, figure-gate.ts,
file-comments-model.ts, file-comments-regions.ts, file-comments.ts, file-trail.ts, file-view-links.ts, file-view.ts,
gesture-clock.js, host-prefix.ts, icons.ts, keybindings.ts, link-opener.ts, math.ts, md-block-start.ts, md-config.ts,
md-links.ts, md-literal-tags.ts, md-sanitize.ts, media.ts, path-links.ts, pdf-cap.ts, pick-held.ts, pinch.ts,
preview.ts, reader-place.ts, region-geometry.ts, session-badge.ts, settings.ts, status-widgets.ts, tab-state.ts,
tab-widgets.ts, url-links.ts, viewer-grammars.ts, widget-prefs.ts). The npm packages those modules import (marked,
DOMPurify, KaTeX, and highlight.js's core with its grammars) are named there and not read: their code is not the
viewer's, the sanitizer's and the highlighter's parses run before the adoption over `clean`, and a write a package makes
onto an element handed to it is its caller's site. The grep finds twenty-six matching lines in seven of those modules,
each judged in the seam test with its reason and none a re-parse under the Rendered box after the adoption:
file-view.ts's, counted below; every other reached module's judged in the seam test, each site with its line and its
reason (JUDGED_SITES, per module), the breakdown stated there and not here, so a site that moves between two modules
moves one record and no restated count. The first spelling of that command lacked setHTML, setHTMLUnsafe and parseHTMLUnsafe and
matched the double-quoted createElement alone; the fork PR review's verification named the gap, and no code line of any
ui/webview module matches those three verbs (the same pattern over every comment-stripped module, 2026-09-20), so the
widening is durability. The sites the grep finds on the road: before the adoption, mdBlock's `codeEl.innerHTML =
hljs.highlight(raw, { language: lang }).value` (escaped text; hljs creates spans and nothing that fetches) and
code-block.ts's wrapCodeLines, both inside the fence pass over `clean`, and after it figureControlGlyph's write of the
control's glyph onto a holder that enters no document, judged with the passes below; the seam test pins each by
execution (the one write in mdBlock before the adoption, the one in a reached local, and code-block.ts's line in
JUDGED_SITES). The passes after the adoption
write a video's style, a list item's class, anchors' attributes (class, title, data-*, target, rel, tabindex, role, an
href set, resolved or removed), new anchors and spans in place of the prose's and the code blocks' text nodes
(`tn.replaceWith(frag)` over text nodes and elements created by `document.createElement`, path-links.ts and
url-links.ts), and the figure controls, each a clone of a glyph parsed once onto a holder that enters no document (the
one such line a reached local holds, file-view.ts's figureControlGlyph), and none re-parses under the box. The same grep
over the whole of file-view.ts finds fourteen sites, the count file-view-seam.test.ts asserts and this paragraph's pin
reads from that assertion: thirteen outside mdBlock, all the viewer's own constant markup (the tray's icon constants,
the bar's Back and Forward arrows, the figure control's glyph parsed once onto a holder that enters no document and
cloned into each control, the loading glyph, codeBlock's numbered rows over escaped or hljs text), and the one inside it
the highlight's write in the fence pass, judged above. file-view-seam.test.ts derives the callee list (every bare call
in the region, with no method call on an imported binding, a require-bound one, gclock, included, in the region or in
a reached local, so a pass in that form is red there rather than hidden from the list), the reached locals, the
imported callees, the module set, the package list and the import forms the resolver follows (synthetic modules
holding each form, the spellings the regex resolver once dropped among them, and a specifier that is not a string
literal asserted to refuse), the judged sites per module and the
whole file's count from the code and pins them (its test "no re-parse after the adoption"), so a new such site anywhere
in file-view.ts or in a reached module, or a new callee or import, is red there until it is judged;
tools/markdown-viewer-plan-gate-adopt.test.mjs holds this paragraph whole and fills its derived figures (the callees,
the imported callees and their modules' count, the module count and list, the two sums, the whole file's count) from
that test's pinned literals, never from a copy, and refuses a per-module count or a count of the imported callees'
modules typed into this paragraph beside them.

**The namespace table.** One probe in the three engines, 2026-09-20 (the real sanitizeMd and wrapLinesHtml from the
bundle, a live-document div's innerHTML set to the split, the figure server's log read after three sentinel round
trips): for each of 108 probe rows, 107 distinct tags (DOMPurify's 47 svg tags, its 25 filter primitives, its 22
disallowed svg tags, `foreignobject` among them, and img, video, audio, source, track, iframe, embed, object, input,
link, base, meta and picture written inside an svg, plus `foreignObject` once more under its camel-case spelling, the
one duplicate), the element on its own line inside `<svg>` with `href`, `xlink:href`, `src`, `srcset`, `poster`, `data`,
`action`, `background`, `fill="url(...)"`, `ping`, `formaction`, `longdesc`, `cite` and `usemap`, each naming its own
URL on the unlisted host. The probe printed 46 kept and 62 dropped: its kept filter left out svg elements, so it flagged
the nested `svg` row dropped while Chromium's log held that row's fill fetch, and it counted `foreignObject` twice; the
counts below are corrected from its rows (the fork PR review's verification re-derived them, 2026-09-20).

| kept inside an svg by the sanitizer (47 of the 107) | after the re-parse in body | fetched, with no chain | the chain judges it |
|---|---|---|---|
| `image` | an HTML `img` (the parser's one tag rename) | its `srcset` (chosen over `src` when both stand): Chromium, Firefox, WebKit | `img`: `src`, `srcset` (FETCH_ATTRS) |
| `svg` (nested) | an svg element | its paint references: the probe carried `fill="url(...)"` alone, which Chromium fetched and Firefox and WebKit did not; with all eight PAINT_ATTRS on the element (the fork PR review's verification, 2026-09-20) Chromium fetched all eight and Firefox and WebKit fetched `mask` alone | paintRefs (fill, stroke, filter, clip-path, mask, marker-start, marker-mid, marker-end) |
| `img` (HTML already: the parser breaks it out of an svg on the first parse) | an HTML `img` | its `srcset`: all three | `img`: `src`, `srcset` |
| `a`, `font`, `title` | the HTML element of that name | nothing, in any engine | not a fetching element |
| the other 41 of the svg list (`altglyph` to `vkern`) | an HTML element of that name (HTMLUnknownElement) | nothing, in any engine | not a fetching element |
| dropped by the sanitizer inside an svg (60 of the 107): `style` (forbidden), the 25 filter primitives (`feImage` among them), the 22 disallowed (`use`, `foreignObject`, `script` among them), and video, audio, source, track, iframe, embed, object, input, link, base, meta and picture written inside an svg (DOMPurify's namespace check) | never reach the re-parse | | |

The class is closed by construction by the move, not by the one instance found: every element the re-parse creates
is judged by the chain over `clean`, because the re-parse runs before it and the created elements are the sanitizer's
own allowed tags under the HTML parser, whose one rename is `image` to `img`; the chain's FETCH_ATTRS covers the two
attributes the created img fetches through (`src`, `srcset`) and paintRefs the paint attributes of a re-created svg,
and no other element the sanitizer keeps inside an svg fetched through any of the fourteen attributes in any engine.
An HTML fetcher written inside an svg never reaches the re-parse (dropped), and one written outside an svg is HTML on
the first parse, kept by the html profile and judged by the chain (img, source, video, audio, track are FETCH_ATTRS;
iframe, embed, object, link, base, meta are not in the profile; input is removed but the disabled checkbox).

**The Copy button after the move.** The fence pass creates each fence's Copy button in the live document
(code-block.ts addCopyBtn, `document.createElement`), appends it into the sanitizer's `<pre>`, which adopts it into the
inert document, and the adoption moves it back with the fence; the DOM keeps a node's listeners across an adoption, and
the Copy case of file-view-figures-gate-adopt-browser.test.ts checks it by a real click (page.click on each of two
fences' buttons) in Chromium, Firefox and WebKit: the handler handed the clipboard write the fence's text and the
label read Copied with the `copied` class, then Copy again after the window, 3 of 3 engines, 2026-09-20. The page is
plain http through the proxy, so `navigator.clipboard` is absent there and a recorder stands in for the write, as
file-view-copy-source-browser.test.ts does; the click and the listeners are the engine's own.

**The guards after the review's first round.** The fork PR's review ruled its first round on 2026-09-20 (six defects,
all in the instruments, none in the fix), and this push answers them. The CI-run guard for the contract is keyed on
the outcome at the boundary and on no list of passes, calls or names: file-view-figures-gate-adopt.test.ts reads the
Rendered box's end state through figure-gate's own gateRefs and unlistedHosts, against the set the gate itself reads
(allowedFigureHosts, pinned equal to the scene's own), in two tests standing on their own and again at the end of each
kind's test, a red naming each leaking element by tag, attribute, value and host (the round-2 review's guards-2: three
plants named the host alone), so an element any pass wrote, moved or created under the box with a fetching attribute
on an unlisted host is red there whatever the pass is called (the three-name denylist over `box` in
file-view-seam.test.ts stays as a second layer). The guard is keyed on figure-gate's own tag table (FIGURE_SEL: img,
source, video, audio, track, image and feImage, with the attributes the gate reads per tag; the scene's FETCHING table
names the same seven tags, pinned equal to FIGURE_SEL, and its attributes per tag are the scene's own copy of the
gate's FETCH_ATTRS, which is not exported and is pinned nowhere until the follow-up PR's fresh-4), so it answers "did
the gate's model see a leak", not "did anything fetch": an element outside those seven tags (an iframe, an object, an
embed, a url() in an inline style) is the gate's blind spot and the product's, not this guard's to catch, since a
guard keyed on the product's own model cannot detect the model's gap, and modelling every fetching element is the
gate's job and not this fix's (the round-2 review's correctness-3, tests-2 and extra6-2, disclosed here and left to
the gate; the plan pin derives the seven tags from figure-gate.ts and holds this sentence and the scene's header to
them). Measured in scratch copies of the head, this scene alone: a post-adoption write of a gated src back into src, a
created img minted in the sanitizer's document and appended under the box, and a new helper named in no list creating
a live img under the box each turned both property-guard tests red with unlistedHosts answering the host (4 of 6 red
each); the base's order turned the two kind tests red on road (a) with the property-guard tests green (2 of 6), an
adoption-time leak being road (a)'s and the order leg's to see, not the end state's. The same read covers a re-parse
since the round-2 review (its guards-1): the stand-in's innerHTML and outerHTML are recorded setters and its
insertAdjacentHTML a recorded method, each write kept with the element's document at that moment whatever spelling
made it (an assignment, a compound assignment, bracket access and Object.assign all reach the setter), and the
end-state read is red on a live one under the box; the seam test's re-parse pattern matches the two names bare for the
same reason. Measured with the scene and the seam test together: `Object.assign(root, { innerHTML: '<img
srcset="http://evil.test/a.png 1x">' })` at the top of keepVideoShape, an existing post-adoption callee, left both
green at the head the round reviewed (67 of 67, the round-2 verification's run: the field was plain and the pattern
matched the assignment spelling alone), and at the head that answered the round the same plant turns the four scene
tests that read the end state red, each naming `div.innerHTML` at its tick, and the seam test's whole-file count red,
13 against 12 (62 of 67). The same scene asserts the ORDER by execution (road (e)): one clock over every write, every
move into the live document and every move-aside the gate makes, and in both kinds the first move of any node of the
sanitizer's body into the live document, read over all moves and not the box-filtered ones, comes after the gate's
last move-aside on that body, with every move-aside landed while the element was the sanitizer's and no fetching
attribute of the body written between the two; a caller pass inside sanitizeMd (mintHeadingIds appending the body to
document.body) and a second registered post-pass in another module doing the same each turned both kind tests red
there (2 of 4 at the head that added the leg). file-view-seam.test.ts's premise guard no longer claims every door: it
derives the registered post-passes from the code (every registerMdPostPass call in the dashboard's comment-stripped
modules, the name resolved to its defining module through the module's `./` imports, a registration it cannot follow
refused), pins the derived list (one, md-config.ts registering math.ts's renderMathPlaceholders), sweeps that body and
mintHeadingIds's for a live-document road, holds md-sanitize.ts's registry to its one writer, and counts importNode
(four) and adoptNode (none) over the whole of each installed dompurify dist's code; the two mutations above turned it
red too (the door sweep naming `document` in mintHeadingIds; the derived list showing the new registrant). The comment
stripper every one of those pins reads through is the TypeScript compiler's comment ranges (ui/test-code-only.ts: the
source parsed, every token visited, the leading and trailing comment ranges removed and nothing else), in place of a
hand scanner that read a regex literal's closing backslash-slash-slash as a line comment and deleted the rest of
settings.ts's hostname line (measured with that scanner before it was replaced); the seam test self-checks the new one
over that module, over md-sanitize.ts and over a synthetic module holding each construct (a regex literal ending in
backslash-slash, a string holding //, a template holding /*, a block comment holding a regex, a URL in a string). The
CI pin in tools/markdown-viewer-plan-gate-adopt.test.mjs reads the property the Tests paragraph states off the block
of the job that runs npm test, found by that step and not by its key, over the block's steps with its YAML comment
lines removed, and nothing in it reads the job's key: the paragraph's sentence names the job by the step it runs, so a
rename of the key alone needs no companion edit (the fork PR review's ruling on its third round's finding pins-2,
2026-09-20: the round-2 push had held the key to a name in the sentence by a separate check, which pinned an
arrangement, and that check is gone); in scratch copies of the head, that module alone, an engine install added to
another job left it green (10 of 10), a Chromium install moved before the job's Test step turned it red with the
sentence to change named (9 of 10), and a Firefox and WebKit install before that step with the sentence reworded to
the run form left it green with the held-whole paragraph pin red, as the same-commit rule intends (9 of 10); after the
round-2 review (its pins-2 and pins-3), a `#` comment in the job's header naming the browser cache green (10 of 10,
where the pin before it read the raw block and was red, 9 of 10), and a restore step for that cache before the Test
step red on the property (9 of 10); after that ruling, the job key renamed alone green (10 of 10) and a Chromium
install moved before the Test step red on the property (9 of 10). Five modules read comment-stripped code (`grep -l
'from "../test-code-only"' ui/webview/*.test.ts`: file-view-seam.test.ts, md-url-view.test.ts,
md-sanitize-viewer-links.test.ts, code-block.test.ts and file-view-links.test.ts, the last two since the fence-pass
pins were re-aimed at the pass's place; the round-2 review's regression-2 found this record and the stripper's header
naming three, and the plan pin now derives the list from the tree and holds both to it), and outside the first three
no test of this branch compares where the chain or the fence pass sits relative to the adoption: code-block.test.ts
reads the fence pass's own shape on the stripped code, file-view-links.test.ts holds an index compare of the fence
pass against the two link passes over the adopted box and not against the adoption, and file-view.test.ts,
tools/file-review-viewer-recipe.test.mjs, tools/upstream-ledger-figure-gate-before-adoption.test.mjs and
tools/markdown-viewer-plan-gate-adopt.test.mjs hold presence pins that name the seam test for it (the round-2 review
found a raw-text compare in each of the last two, and a `//`-line filter standing in for a stripper in the plan pin),
and the tools modules, which run in CI's shell job with no node_modules, cannot reach the compiler; the ledger entry's
file count is derived by `git diff --name-only origin/main...HEAD`, the merge-base form, at the head.

**Scope.** Unreachable through the VS Code panes, whose CSP blocks remote figures (`img-src ${webview.cspSource} data:`,
extension.ts). Reachable through the kernel-served dashboard and the iOS web app. What leaks is the IP address, the
time, the user agent and the path; the kernel sends Referrer-Policy same-origin, so no referer. The engine measured is
Playwright's WebKit build, not literal iOS Safari, so the iOS statement rests on shared engine behaviour and not on a
device test. In the dashboard, Safari was reachable through an HTML img and through an svg image spelt `xlink:href`,
Firefox through an svg image in either spelling on a long note; Chromium made no request at the base for any figure
measured.

**Tests.** file-view-figures-gate-adopt-browser.test.ts, above: red in WebKit at 2d41e5c9b in all three scenes, green
in Chromium and Firefox there, green in all three engines after the fix. Its fourth scene, the fence hole (three raw
multi-line fences, an svg image with `src`, with `src` beside a gating `href`, and with `srcset`, and the
`language-js` control): red in all three engines with the fence pass after the adoption (the figure server's three GET
lines) and green in all three with the pass before the chain, one placeholder per fence. Its fifth case, the Copy
button under the moved pass, clicked for real on two fences: green in all three engines. Its sixth case, the svg
anchor split across lines in a raw fence, with an author's id and without one, and an author's prose anchor spelled
with `xlink:href`, all three marked dead with the title in the rendered page and the prose's anchor target unmarked:
red in all three engines at the head before the mark for the id-bearing anchor (no class, no title), green in all
three with it. file-view-figures-gate-adopt-svg-browser.test.ts, the second leg: red in Firefox and in WebKit at
2d41e5c9b, green in Chromium there, green in all three after the fix. Both legs skip where Playwright's engines are
absent. In CI, the job whose step runs npm test has no Playwright browser install and no restore of Playwright's
browser cache before that step (the job's own steps, the job found by that step and not by its key, read off
.github/workflows/ci.yml by tools/markdown-viewer-plan-gate-adopt.test.mjs; what another job installs, or this job
installs after that step, does not bear on it), so in CI the legs skip and the node scene runs:
file-view-figures-gate-adopt.test.ts drives the real openFileView and openUrlView under plain node over a stand-in
with two documents, the sanitizer's body inert and the viewer's document live, and pins by execution that no node
entering the live document carries a fetching attribute on an unlisted host or a page-relative path (an img's src and
srcset, a source's, a video's src and poster, an audio's src, an svg image's href or xlink:href, an svg paint
reference, a figure inside details, a folder figure, and for a URL document a relative figure resolved against the
document's directory; read at every move into the live document whose parent is the viewer's box or stands under it,
so a node a later pass brings in at any depth is read at its own moment), that no write of such an attribute lands on
a live-document element across the render, that nothing under the box carries one once the render is done, that the
gated figures stand as placeholders holding their sources in data-fv-gated-* and a click on the host restores exactly
them, and that the folder figure is requested through /file. Red on four mutations of file-view.ts in scratch copies
of the head (2026-09-20): the base's order (the adoption first: 16 leaks at the adoption in the file kind and 4 in the
URL kind), the gate alone moved after the adoption (13 and 2), one added post-adoption write of a gated src back into
src (5 live writes and 2), and one added post-adoption line appending an img minted in the sanitizer's document with a
src on an unlisted host into the box's first paragraph (1 leak at that adoption in each kind, read tree-wide under the
box; the top-level read alone stayed green in the file kind); green at the head. It sees no bytes: a leak there is an
attribute the browser would fetch through, judged over the box's end state by figure-gate's own gateRefs and
unlistedHosts (the property guard, one test per kind on its own, and again at the end of each kind's test) and by the
scene's own oracle, which alone sees a page-relative leak; the same scene asserts the order by execution, its road
(e), and the guards paragraph above records both with their mutation runs; the engines' loading is the legs' and
DOMPurify's document is the seam test's. file-view-seam.test.ts pins the order in mdBlock (sanitize, rewrite, gate on
`clean`, then the adoption, and no figure pass over `box`) and holds the inertness premise, which no node test can
execute: its test "the inertness premise, held where CI runs" pins the sanitizer's profile literal and its keys at run
time, the config the sanitize is handed, sanitizeMd's body, the installed DOMPurify's RETURN_DOM branch with its one
road into the live document (a clone under an allowed shadowroot attribute, which no profile here allows), the passes
that run over the body inside sanitizeMd before the chain (mintHeadingIds and every registered post-pass, the list
derived from the code) opening no door to the live document, the whole of each dist's code holding importNode at four
sites and adoptNode at none, and `clean` reaching the four chain calls and nothing else before the adoption (the
review's refuters measured that one added profile key, `ADD_ATTR: ["shadowrootmode"]`, made DOMPurify clone the body
into the live document with every CI-run module green and WebKit fetching the gated figure again); since the fork PR's
round-2 push it also pins the fence pass's place (on `clean`, between the sanitize and the chain's first call) and its
one read of `clean` beside the four chain calls, and, in its test "no re-parse after the adoption", the re-parse
population above, derived from the code, with the whole file's count, the two property names matched bare since the
round-2 review. The order pins in file-view-seam.test.ts, md-url-view.test.ts and md-sanitize-viewer-links.test.ts,
and since the fence-pass pins were re-aimed code-block.test.ts's slice of that pass and file-view-links.test.ts's
compare of it against the two link passes over the adopted box, five readers of the stripper, read comment-stripped
code since that push (ui/test-code-only.ts, the TypeScript compiler's comment ranges, since the review's first-round
ruling; a comment quoting the pinned lines above an adopt-first body satisfied the raw-text pins in the round's
reversion runs), and the assertion messages in file-view-text-size.test.ts, file-view.test.ts and the recipe pin, and
the comments in render-sanitize.test.ts and md-sanitize-viewer-links.test.ts, that stated an order the assertion did
not check now claim presence, the order being the seam test's (file-view-text-size.test.ts's sits in a browser-gated
test that skips where no engine is installed, so in CI it does not run). md-url-view.test.ts pins the URL kind's
resolution before the adoption; tools/file-review-viewer-recipe.test.mjs pins the sanitize and adoption statements as
presence pins; tools/upstream-ledger-figure-gate-before-adoption.test.mjs holds the ledger entry's file list, its
count and its engine statements to the tree and the legs, with a presence pin for the fence pass's read;
tools/markdown-viewer-plan-gate-adopt.test.mjs holds this section's sentences to the code, its comment and the leg,
with presence pins for the chain's calls and the fence pass's read, the order being the seam test's. The remedy for
the legs' skip in CI is a step in that job installing Playwright's engines (Firefox and WebKit, or all three) before
npm test; the plan pin reads this paragraph and the job together, so taking that remedy means rewording the sentence
above to the pin's other sentence, which says the legs run there (CI_RUN in that module, beside CI_SKIP, the sentence
above), and the pin then holds the job to an install of Firefox and WebKit before its Test step instead of to none;
the pin does not fight the remedy, it names the sentence to change.

## Follow-on: Link navigation (2026-09-19)

The user asked (2026-09-19) for a way back after following a link inside a file: a link to another file opened its
target in place of the file being read, and returning to that file meant finding it again, in the Files pane's Recent
list or by hand, with no Back anywhere. The viewer project above is complete; this follow-on gives the viewer a
navigation trail of its own and lands as one PR at the feature tier, on branch `filereview-linknav`, cut from
34142c262, the fork's main at the time, and, since the PR's file review found the remote picture's tab a new
credentialed request (L3, L6), on the owner's word as a privacy surface whatever the tier. The branch's adversarial
review before the PR ran two rounds, named below as the review's round 1 and round 2; the maintainer session's review
of the PR (2026-09-20) is named the file review. Its contract is kept outside the repo; this section records what was built,
with the build's deliberate departures from that contract recorded as the decisions, and what is left for the owner to
rule on. The file review's rounds are named the file review's round 1 to round 5, the rounds it has ruled (its fixlists and
rulings are kept outside the repo in the maintainer's notes, one pair per round); the author's own verification after each
round's fixes, by a verifier of the author's, is named the author's closing pass after that round, never a round of either
review, and its findings carry the ids behaviour-N, records-N, coverage-N, guards-N, attribution-and-gates-N, reader-N and
tree-N, which no fixlist of the file review holds. The maintainer's read of the whole PR at one head before landing is named
the file review's landing round, with no number, and the findings its fixlist carries keep that fixlist's own ids (fresh-N,
rules-N, regression-N, tests-N and extra-N with a digit before the hyphen), none of the author's family. The author's
own verification after the landing round's fixes is named the author's closing pass after the file review's landing
round; its findings' ids (census-N, and records-N of the family above) stand in its commits and in the notes outside the
repo, and the records here name the pass alone, since the attribution module reads a pass's name to the digits of the
round it followed and the landing round has none. A record naming a
round names the review it belongs to first (ui/webview/linknav-records-attribution.test.ts holds this, in every checkout,
over every unit of the files the branch created and over every unit in the tree that names the file review, names the
author's closing pass, or carries an id of the author's family, a phrase outside the created files judged where the review
named nearest before it is the file review or the author's pass; the file review's round 5, extra5-2: the sentence had claimed every record the branch wrote,
which held only on a road that read the diff, and that road runs in no CI checkout).

**What existed.** A link in a rendered file to another file (`[x](other.md)`, `other.md:7`, `other.md#section`, a
picture or PDF path, a wikilink, an embed chip) opened that file in the SAME viewer card: re-opening replaced whatever
was up and never stacked (openFileView's replace path, the body delegate's openpath arm, openLink). The first file's
reading place was already written by runLeave (RememberedPlace: the reader's place in the text, the view it was read
in, the scrollTop and the open folds, keyed by path plus session, in a page-life map and on the Files pane's Recent row
in localStorage; Slice 6) and re-seated on a targetless reopen (pendingPlace); an open with a line or heading target
ignores the memory. No navigation stack, no Back or Forward, and no history API use anywhere in the webview: the
browser's Back, Alt+Left and a back-swipe acted on the shell page, and the one "Back" was the Files pane's "‹ Files"
link, which closes the viewer to the listing. A plain click on an embedded figure (`![](fig.png)`) did nothing; with the
Comments panel open in Rendered mode it offered a comment (file-comments.ts onImageClick) and a drag drew a region
(file-comments-regions.ts). A picture opened on its own (imgBlock) has no zoom.

**Decisions.**

L1. **A trail.** `ui/webview/file-trail.ts` holds the trail as a plain state, `{ back, current, forward }` of entries
`{ path, sid, view }`, pure functions over it (`trailRoot`, `trailPush`, `trailBack`, `trailForward`, `trailSetView`,
`trailEnd`, `trailBackTarget`, `trailForwardTarget`) and the one live instance (`liveTrail`, `setTrail`), beside the
viewer's other page-life memory (file-view.ts `rememberedPlaces`). How openFileView tells an open from INSIDE the viewer
from one from OUTSIDE, with no flag every caller must remember: the viewer's own opens go through one door,
`openFromViewer` in file-view.ts, which sets a module-level tag (`trailNext`: push, back, forward or reload) and calls
`openLinkedFile` as the body's delegate always has (the host's opener, files.ts `openHere`, or the default open; both
reach `openFileView` in the same call, which reads and clears the tag at its top, before its close guard, and the door
clears it again in a `finally`). No other caller sets the tag, so an untagged open is from outside by construction: the
Files pane's rows and its Recent list, the file browser's rows, a chat path pill (render.ts openPath), a Waiting pane
link (waiting.ts), the shell's relay. The tag decides the move (`moveTrail`, run in the replace path after `runLeave`
has written the leaving file's place): a push puts the shown file behind the opened one and clears the list ahead; an
untagged open roots a new trail at the file; the conflict bar's Reload file tags itself reload and moves nothing. The
body delegate's path links are the pushes: a Markdown link to a file, a bare path in the text, a `:line` or `#section`
target to another file, a wikilink (md-config.ts renders `[[Note]]` as an anchor to `Note.md` beside the note, which
linkMarkdownAnchors marks as a path link), and L3's figure open. A target inside the shown file (`report.md:40`
followed from report.md) replaces the card and pushes nothing: the trail's entries are files, and a jump inside one is
no step between files (the contract's pushes were to another file; a duplicate entry would have made Back re-open the
same file at the same place). A section link of the same document scrolls and pushes nothing (the delegate's fragment
arm opens no file). A web address opens a tab and pushes nothing (its anchor arm). The entry's `view` is the view the
reader left the file in, read at the move off the RememberedPlace `runLeave` has just written, by the file's key
(`placeKey`), at every move, a reload included; a picture or a PDF writes no place and records none. Closing the viewer
ENDS the trail (closeFileView, once its guard has passed): the person left the review, and a reopen of the same file
from Recent starts a new one. The alternative, keeping the trail for the page's life so that such a reopen finds its
Back again, was not taken: a Back reaching into a review the reader had closed would move the card on nothing they did
since. A URL document replacing the viewer (openUrlView) ends the trail the same way, its entries being files; the
contract named no such case. Held by file-trail.test.ts (the pure cases, the three wiring pins, and the conflict bar's
Reload file driven in Chromium at the module's end: a link push, Edit, a change, a Save refused as changed on disk,
Reload file, the fresh card's Back still titled with the report's name, then Back to the report with the reloaded file
ahead) and file-trail-browser.test.ts (the Files page: a link followed, a Recent row and the relay rooting the trail,
the section link, the web address, the same-file target, the close; the chat modal: the default opener).

L2. **Back and Forward.** Two glyph buttons in the icon family (icons.ts `ICON_BACK`, `ICON_FORWARD`: an arrow left and
an arrow right), the bar's first group (`.fileview-group.fileview-nav`), before the pane's "‹ Files" link, which keeps
its meaning, closing the viewer to the listing beneath it (file-view.test.ts pins it unchanged). The title and the
aria-label name the target ("Back to report.md", `navTitle`); with nothing that way the word stands alone and the button
wears `aria-disabled`, the text-size ends' precedent (never `disabled`, so a focused button keeps the keyboard; the
sheets' one disabled dress applies, no new rule). Built once per open from the trail as the open left it and never
rebuilt: every step is an open that builds a new bar. A press re-opens the entry through `openFromViewer` with NO target
(`at` null), so the remembered place re-seats the file where it was left (pendingPlace), and the entry's recorded view
is the view for that open (this open's `fmt.md` copy, unsaved, as a line target's Raw is); the replace in the same tick
is the acknowledgement. The chords: Alt+Left and Alt+Right, and on a Mac Cmd+[ and Cmd+] as well (`navChord`, pure over
the event's fields), through ONE document keydown listener in the capture phase, installed per open and removed through
the viewer's close hooks by both exits; it stands down when the key was already prevented, when a text field holds the
keyboard (`isTypingTarget`: a text input, a textarea, a select, a contenteditable), while the editor is open (`editing`,
whatever holds the keyboard then), and when no viewer is up, and otherwise takes the browser's default (its history
step, which would leave the page under an open viewer) whether or not the trail has a step that way (the contract asked
for the chords while the viewer is open; a chord with no step that way is taken too, so a chord outside a text field,
with the editor closed, never navigates the page away). The stand-downs are the exception, and the record names it
rather than reading as an absolute: with a text field focused (the comments composer, a search field, the plain-textarea
editor) or while the editor is open and a bar button holds the focus (Save, Cancel), Alt+Left reaches the browser
unprevented and is its Back on Linux, so the page under the open viewer leaves and an unsaved edit goes with it (no
beforeunload guard exists in the webview or the shell); the review's probe verified this on 2026-09-19 with a real key
into headed Chromium and Firefox under a virtual display (Windows binds the same key to Back and was not run; on a Mac,
Alt+Left in a field is the caret's word step, and Cmd+[ under the same stand-down was not run, open point 6). CodeMirror
itself, focused, binds Alt+Left to a cursor motion (its default keymap) and kept the key at every caret position tried.
The browser legs cannot show that half: a synthetic key from Playwright does not run the browser's Back accelerator (the
probe saw the page stay with no viewer up), so file-trail-browser.test.ts asserts that the chord is not the trail's with
a field focused and that the default is taken with the keyboard on the body, and no test drives the leave. Whether the
listener should take the default in the stand-down cases too, stepping nothing, is the owner's (open point 9). Inside
the dashboard shell a second stand-down applies: the shell's pane-focus script (kernel.py `_LANDING_FOCUS_JS`) wires a
capture-phase keydown listener on every pane document as the pane loads, ahead of the listener a later open adds, and
takes Alt+Left and Alt+Right on a non-editable target as the move between panes (preventDefault, so `onNavKey` sees a
prevented key and returns), so in a shell pane (the Files pane, a chat pane's modal) the arrow chords move the pane
focus and the trail's are Cmd+[ and Cmd+] on a Mac and the two buttons everywhere; on the standalone Files and chat
pages, which the browser legs drive, all four chords step the trail. Read from the listeners' order, not driven (open
point 10). The Recent list keeps its meaning: a Back or Forward open in the Files pane records the file as any open
there does (openHere), moving its row up. The GROUP is HIDDEN when neither direction has a target (`nav.hidden`, set
before the group is appended, which the sheets take out of the flow with its gap, styles.css `.fileview-group[hidden]`):
on an open with no step either way, the ordinary open from outside, the bar rows no pair; once a step exists one way the
group shows whole and the button without a target wears `aria-disabled` alone, so the two glyphs keep their places from
one step of a trail to the next. The ground, re-decided in the file review's round 2 (extra8-2): the round-1 record kept
the pair dimmed, the contract's shape, on the claim that the file review's round-1 refuters had found no rule in ui/CLAUDE.md or in
the code that hides a control with nothing to do, and that claim was false. T367 (the user 2026-09-12; file-view.ts's
GitHub-link section, styles.css's `.fileview-gh` comment) is that rule for this bar, with a worked precedent: the greyed
GitHub link and its caption were removed rather than dimmed from a file outside a repository, the unit hidden and out of
the row's flow; the clause the round-1 record cited, that a GROUP whose children are all hidden hides (the view group's
sync), is the same decision's second clause and not the whole rule. The dimmed dress is the bar's other precedent, older
than T367 (the text-size ends and the Save in flight, styles.css's one disabled rule, `.fileview-btn:disabled,
.fileview-btn[aria-disabled="true"]`, whose text entered the sheet on 2026-09-07, where T367 entered file-view.ts on
2026-09-12, both by `git log -S`), and the two tell apart by whether the control can become live during this open: an
end of the text-size table does at the next press the other way, a Save in flight can once the save has answered, while
a Back with no target cannot until a link is followed, which builds a new bar, so a pair with nothing either way is not rowed.
What the hide buys, measured by the round-1 refuters in Chromium: about 74 px of a 359 px bar at a 380 px viewport, at
the cost of the file name moving 74 px on the first link follow of every trail, a shift the bar built once per open
otherwise avoids. The contract's L2 clause (aria-disabled alone when empty) is corrected to this with the reason; the
pins that held the dimmed pair (file-trail.test.ts, tools/markdown-viewer-plan-linknav-review.test.mjs) hold the hide,
and file-trail-browser.test.ts and file-view-text-size.test.ts's bar case read the hidden group's attribute and its
empty client rects off the bar on a fresh open, then the group showing after a link is followed, Back live and Forward
dimmed. Whether the contract's dimmed pair should come back instead is the owner's (open point 13). Held by file-trail.test.ts (the titles, the chord table, the bar and listener
pins) and file-trail-browser.test.ts (Back at the block, the scrollTop and the view; Forward; the chords with and
without a text field and under a prevented key; the default taken with and without a target).

L3. **A figure opens in detail.** Every picture a rendered file embeds (`![]()`, an `<img>`, an image wikilink embed),
with the exceptions this decision names (a picture with nothing to open, a gated placeholder until its load, a figure
under the size floor, a figure inside a link holding more than it), wears an "Open the picture" control (file-view.ts
`decideFigureControl`, the one place a control is added or removed, over the verdict `figureWantsControl`): a glyph
button of the bar's family (icons.ts `ICON_EXPAND`, two arrows out of opposite
corners; `button.fileview-btn.fileview-icon.fv-figopen`, the words in its title and aria-label, found by its mark
`data-fv-figopen` and never by its class), in the tab order as any button is. Whether the control stands is decided
from the figure AS IT IS NOW, by that one function, and decided again at every event that changes what it reads: the
paint (mdBlock, `addFigureControls`), the picture's load and its error (`armFigureControls`) and each change of the
figure's own laid-out box (`watchFigureBoxes`: one ResizeObserver per open over the figures of the Rendered box,
armed at each text paint through the seam's onRendered, the first paint's included, which hears every reflow of the
figure whatever moved it, the body's width or a text-size step; the file review's round 2, below); the verdict reads the figure's state off the element (`figureState`: `complete` and
`naturalWidth`, the browser's own record: fetching, loaded, failed, or a stand-in outside a browser, which carries no
`complete` and is decided from its source alone), and a figure still fetching, or one that failed, gets none. The file
review found five findings with that one cause, the control decided once at the paint from what was known then, and
they were fixed as one re-decision rather than five patches: the floor read once at the load (below), a failed 0 by 0
figure's control laid over the link before it, a fetching `<picture>`'s control and plain click opening the fallback
src, and a control never re-judged against a `data:` candidate the browser then chose. It is the img's SIBLING, inserted right
after `figureAnchor`'s climb (the img, its `<picture>`, the regions layer's wrap, a link holding the figure alone),
never a wrapper: the panel pairs pictures by img order and `data-fv-src`, the regions layer wraps THE img, the
reader's place and the anchor map read the flow as the browser laid it, and a wrapper standing in the author's flow
changed a figure's own layout (the regions layer's 2026-09-06 review). The sheets lay it over the figure's top-right
corner from that place with no measuring (`.fileview-md .fv-figopen`: the family's inline-flex box aligned to the
line's top, a zero-width margin box of a 28px negative left margin and a 6px right margin around the 22px glyph, and a
6px relative offset down), positioned so it paints and is hit above the layer's overlay while the panel is open;
transparent at rest, revealed by the pointer over the figure or over itself and by a keyboard focus, kept visible on a
device with no hover, every reveal under `screen`, so a print shows none of it and the print block carries no line for
it (the print block is pinned whole, and the in-flight print follow-on adds lines inside it). A figure the author
floated with `align` stacks sideways: the control floats with it, a left float's at the top-right corner as before, a
right float's at the top-LEFT corner (`fv-figopen-left`, `fv-figopen-right`: a later right float sits left of the
earlier one, and the far edge cannot be reached without the figure's width). The text walks skip it as a control
(anchor-map.ts and reader-place.ts CONTROL_CLASSES); the Rendered pairing leaves it out of the top-level nodes beside
an html-block figure as it leaves the failed figure's label (anchor-map.ts `isFigureCompanion`, the predicate Slice 7
recorded as `isFigureLabel`); the label goes after
the control when both stand (`figureLabelAfter`). What it opens (`figureTarget`): a remote picture (an http or https
source, a protocol-relative one) in a tab, never the viewer, the web test run FIRST, before the model's join, since
`figurePath` reads a protocol-relative source as an absolute path of the disk (read after the join, a `//host/pic.svg`
source opened the viewer on the kernel's /file route at that path, a 404 and a bogus entry on the trail; the review's
round 1); else the file named by the candidate the browser chose for the figure, as the author wrote it (`chosenSource`,
the review's round 2: `currentSrc`, when it is set and is not the img's own src, matched against the srcset carriers, a
`<picture>`'s sources then the img, and named by the authored spelling rewriteFigureSrcs kept beside the rewritten
candidates; else the src by pictureDest's rule, the browser having chosen the src itself or the figure carrying no other
candidate; a figure still fetching has NO target (`figureState`, read first in `figureTarget`: `complete` false), so its
control waits for the load and its plain click opens nothing, since currentSrc is empty while the source is on the wire
and chosenSource read that as the src (the file review: the control the paint added, and the plain click, on a
`<picture>` or a srcset figure still fetching opened the fallback the browser never asked for and put that file on the
trail), nor has a figure that FAILED (the same read: `complete` true and `naturalWidth` 0), so no gesture opens it (the
file review's round 2, below); the two are the refused states of ONE rule, a target only for a state with a picture to
name (`figureHasPicture`: `loaded`, the browser having answered with a picture, or a stand-in outside a browser, the
node suites' DOM, decided from its source), the rule `figureWantsControl` withholds the control on too, so a state
`figureState` gains later is refused by both readers with no edit to either (before the file review's round 3 each
reader named the two states it refused, a list a new value passes; a guard refuses on its safe side for any value it
does not know; the pin that holds the refused states' literals absent reads every string literal of file-view.ts as the
compiler reads it, in either quote, a template span or an escaped spelling alike, and a regular expression literal by its
text (ui/webview/source-units.ts, the reader ui/webview/linknav-records-attribution.test.ts shares; before the file review's
round 4, regression-2 with extra6-1, three copies of the pin matched the double-quoted spelling alone and a single-quoted
comparison passed them all while their messages claimed no member's literal stood anywhere), but the type line's and
`figureState`'s; the pin reads whole values equal to a member, so a reader that uses the word as an identifier key (a
lookup table `{ failed: true }`), assembles it at run time (a join, a substitution template; a chain of literals joined by
`+` is read as the value it computes), tests a prefix or a substring of it or compares case-folded
stands outside the pin, which its message says and its boundary test pins by execution (the author's closing pass after
the file review's round 4, guards-1 with records-11: the pin's comment had claimed any spelling; the identifier form is
left unread on purpose, since file-view.ts names a save hook `failed`, which a key reader would red at rest or force a
rename of product code for a pin); and the pin is file-wide on purpose, so a literal `"failed"` or `"fetching"` for anything
else in the module must be spelled another way, which the author's closing pass after the file review's round 3 recorded,
records-3, while prose may quote the word, since a comment is no literal); the target is read
again at the click; the failed figure's label, `failedSource`,
delegates to it; read from the src alone, the control opened the fallback src a `<picture>` or a srcset figure had
skipped), joined by the model's `figurePath` (file-comments-model.ts, the join rewriteFigureSrcs fetched through, so the
picture opened is the one shown and its request is the paint's), through the figure's own door,
`openFigureInViewer` (openFileView itself with the trail tag set to push and cleared in a `finally`, as
`openFromViewer` sets and clears it, and not the host's opener that door calls), so the shown file goes onto the trail
and Back returns to it at the figure's place, and the picture takes NO Recent row: in the Files pane the host's opener
(files.ts openHere) records every file it opens, and eight figures opened from one report evicted every other file's
row and the reading place stored on it (the file review; the list holds eight). The default taken: a picture reached
from its report is a step inside that report's reading and no file the reader chose from the pane, so the report's row
stands and Back reaches the report through the trail, while a Back or Forward open keeps taking its row (L2); whether a
picture opened from a figure should take a row instead is the owner's (open point 12). Nothing for a `data:` URL
(inline bytes a tab will not show) or a figure with no source, which get no control. The tab is the one request this
follow-on adds (the file review's HIGH 1; L6): a plain click on a LOADED remote picture, its control, and a
Cmd/Ctrl-click on it, three gestures through one arm, all call `openUrlTab` (`window.open(href, "_blank",
"noopener,noreferrer")` in the web dashboard; the function's other arm, the host's openExternal, is the VS Code
webview's, and the clause below holds in either arm; the control at any time, and the two clicks on the picture where
the press reaches it, the Comments panel closed or the pointer coarse, since with the panel open on a fine pointer the
layer's overlay takes a click on the picture, modified or not, and offers a comment), a top-level navigation to the
picture's address: a second,
differently kinded, credentialed request to a host the page had requested the image from, since a figure opens a tab
only once LOADED, and the page's image request to that host preceded its load (answered by the host, or by the
browser's cache from an earlier answer). "Requested", not "fetched": before the round-2 fix `figureTarget` refused the
fetching state alone, so a FAILED remote figure kept its target and its plain click opened the tab with no image
answered, a first contact where the image request never left the machine (a content blocker on the dashboard) or the
host answered 404, and the file review's round 2 (extra5-4) found the clause false there; a failed figure now opens
nothing on any gesture, so the clause holds for every figure that can open a tab. The modified click opens the
picture's own address and never the kernel's /file URL, since openFigure's web arm runs before its /file-tab branch
(extra5-3: the record had named two gestures and given the modified click the /file URL). Before this follow-on only
an author's link opened such a tab. The gate is not bypassed: no request reaches a host the gate still holds
(file-view-figure-chosen-browser.test.ts, at a context-level route with the real window.open, the route and the page's
fetch wrapper installed BEFORE the report opens so the open's own window is watched, extra7-1: none while gated and
none at the open, one image request per remote figure at the gate's lift (the `<picture>`'s source, and the failed
img's src, answered 404), one document request per tab from each of the three gestures, none from the failed figure's
clicks, never the src's address, and nothing to any other host through window.fetch, read off a never-drained list the
wrapper keeps, tests-2). What rides, measured in the tree by that leg in Chromium (tests-3, fresh-3) with three cookies
seated on the host before the open, SameSite=Lax, SameSite=Strict and SameSite=None with Secure: each image request
carried the None cookie alone, and each tab's document request the Lax and the None cookie, never the Strict one. So
what is new is the request's kind and the Lax class it brings, and not credentials on an image request as such, which
the None class rides in Chromium; the table is Chromium's alone (fresh-3's refuter saw Firefox carry the None cookie on
the image request too and WebKit drop it there, a difference between engines the leg does not measure). The records
pass's earlier measurement (2026-09-20, a real HTTP server's log, a scratch leg kept outside the repo beside the
contract with its record, Lax and Strict seated): the image request came with no cookie and with the page's origin as
referer, `http://notes-api.test/` and nothing of the page's path (`sec-fetch-dest: image`, `sec-fetch-site: cross-site`;
the origin alone is established by a second real-server probe of 2026-09-20 from a page at `/some/dir/page.html?tab=chat`,
its record beside the first's, since the first probe's page sat at the origin root, where the page's address and the
origin are one string and the record could not tell them apart, and the sentence written from it had claimed the page's
address, which the file review's round 3 found the record could not show; Chromium's default
`strict-origin-when-cross-origin` sends the origin on a cross-origin request; the kernel-served dashboard sends
`Referrer-Policy: same-origin`, kernel.py, so there the image request names no referer), and each tab's document request
(`sec-fetch-dest: document`, `sec-fetch-mode: navigate`) came with the Lax cookie, without the Strict one, and with no
referer, in both probes (the tab is opened by `window.open(href, "_blank", "noopener,noreferrer")`, `openUrlTab` in
file-view.ts, and `noreferrer` sends none; the policy alone would have sent the origin on the cross-origin navigation as
it did on the image request, so the record rules the policy out as the cause, which the author's closing pass after the file review's round 3 (behaviour-1) found the
earlier sentence had named). So the follow-on is a privacy surface and lands on the owner's word whatever its tier, with the two roads
priced in open point 11. A gated
placeholder (figure-gate.ts) gets none until its figure is loaded: `armFigureControls`, one capture-phase pair of `load`
and `error` listeners on the body per open beside the labels', runs the decision at the load and at the error (the
placeholder's click, a settings change restoring it, the chat page's heal landing a retry). A URL document (openUrlView) gets none: its
figures are the web's. Two more shapes get none, the review's round 1 (a control the sheets' fixed margins laid over a
figure's neighbours took the clicks meant for them, itself transparent): a figure under 48 CSS px on either side
(`FIGOPEN_MIN_PX`: the control's 22px box, its 6px inset and as much figure again; a badge, an inline icon, whose
plain click still opens them where no link holds them), measured from the loaded picture's laid-out box while it is in
the document, else its own size (`figureBox`, `figureTooSmall`; a loaded figure alone has a box to measure, `figureState`), read wherever the
decision runs: in a browser a picture the browser is still fetching at the paint (mdBlock, `addFigureControls`) gets none
then, and its load or its error (`armFigureControls`) runs the decision with the picture's size known; a picture the
browser already holds (the report re-opened: Back, Forward, a second open after a close; no request leaves for it) is
complete at the paint and is decided then, from its natural size, since mdBlock's box is not in the document yet, and its
load event, which fires all the same, decides it again over the laid-out box (the file review's closing check: at a 381 px
re-open the 761 by 76 picture's paint-time control left at its load, the picture laid out 324 by 32; at 900 it stood;
file-view-figure-floor-browser.test.ts); and the floor is read
again at each change of the figure's own laid-out box (`watchFigureBoxes`: one ResizeObserver per open over the
figures of the Rendered box, armed at each text paint through the seam's onRendered, the first paint's included
(nothing is observed at the open: the body is empty then), and dropped with the viewer, running the same decision for the figure whose box changed; a report of 0 by 0
runs no decision, a rule over the report whatever produced it: a 0 by 0 report decides nothing, and the figure is decided
by its load or its error, by the gate's restore or by its next report with a box (the file review's round 4, regression-3:
the reason before it named two roads to such a report as the only ones, and a loaded figure the author gave no box was a
third); the viewer's hide and a gated placeholder's img until its click are transient reports, on both of which the show
or the restore reports the real box, which is decided, while a decision over the hide's report would take a standing
control off a figure that is merely hidden and the show would put it back, a remove and an add the reader never sees
(found before the file review's round 3: decided over it, `figureBox` then fell back to the picture's own size and a
figure hidden under the floor at its real width gained a control while hidden and lost it at the show); the final report
is a LOADED figure whose real box is 0 by 0, an author's `<img hidden>` or `<img width="0">`, both kept by the sanitizer,
which reports 0 by 0 for as long as it stands and gets no control by the floor and not by the skip, which decides
nothing: `figureBox` reads the laid-out box of a figure in the
document as it is, 0 by 0 included, and falls back to the picture's own size only for a figure not in the document
(mdBlock's box at the paint), so such a figure's load decides it under the floor (the file review's round 3,
correctness-1: the fallback ran for any zero-sided rect, the hidden picture was measured over the floor at its own size,
and its control lay 28 px into the words before it, where it took the click meant for them and opened the picture the
author hid; the same read makes a load while the viewer is hidden a decision over 0 by 0, so a standing control leaves
at that load and the show's report of the real box brings it back, where before the control stood through the hidden
load; the floor leg drives both authored shapes beside prose, the click on the words, and the hidden load); the
residual the skip leaves, a figure hidden after its load by any road but the viewer's own keeping a standing control
until its next report with a box, has one road in the product, a `<details>` folded by the reader (an expanded callout,
`> [!note]+`, renders as a `<details open>`), on which the control is harmless by a mechanism that is not the skip: the fold reports nothing, so
nothing reaches the observer while the callout is folded, the control is folded with the figure and stands over no prose,
and the first report with a box after the reopen decides the figure again (the file review's round 4, ui-1, measured in
the three engines from plain authored markdown: folded, the figure kept its box and its control, both out of the
pointer's reach; reopened at the width it folded at, no report and the control stood; reopened after a narrowing, the
report removed the control under the floor; the record before it said the product had no such road, reached only by an
injected stylesheet), so a road added later that hides a figure and reports for it decides the figure itself or lifts
the skip for it (recorded, not built against); the watch
is armed at each text paint and not before the first, since the body is empty when the open sets it up (the file review's
round 3, tests-4: an arm there observed nothing on any road, measured in Chromium over the fresh open, the replace, Back,
Forward and a reopen, and was removed), which is the
reflow itself whatever caused it: the pane dragged, the Comments aside opened or closed, the window resized, or a
text-size step (A-, A+, Ctrl/Cmd + wheel), which re-measures the 80ch column at a constant body width and so reflows
every column-capped figure with no width report; so a figure the column narrows under the floor loses its control and
one it widens past gets it back (the file review's measurement at an earlier head: read once at the load, a 761 by 76
figure narrowed to 323 by 32 kept its control, which hung over the figure and took the click meant for the prose,
where the note reopened at that width had none; and its round 2, correctness-1 with four findings of the same cause:
decided again from the width watch's repaint alone, the one road the round-1 fix wired, a band a text-size step had
narrowed under the floor kept its control and one the step widened past never gained it, so the event is the figure's
reflow and not one of its causes; a value measured once against a condition that can change is re-read on the event
that changes it); a control removed while it holds the keyboard hands it to the viewer's body first
(`removeFigureControl`, through a per-open register of the body's takeKeyboard, since the decision is module-level and
the hand-over is the open's: the file review's round 2, ui-4, where the removal dropped the focus to the document's
body and PageDown, the arrows and End scrolled nothing until a click); a picture that failed to load gets none and
opens nothing on any gesture (`figureTarget` refuses the failed state as it refuses the fetching one, the verdict the
control is withheld on, so the two readers of "is there something to open" agree: the file review's round 2,
regression-3 with extra5-4, where the target refused the fetching state alone, so a plain click on a failed local
figure opened the missing path in the viewer and pushed it onto the trail, and one on a failed remote figure opened a
tab at a host whose image request had answered 404; and with an empty alt no box: at the head before the one decision
a 0 by 0 failed figure wore a control laid 28 px to its left, over the link before it, which took the click meant for
that link, the file review; a failed figure with a non-empty alt has the alt text's box, which the state leg clicks),
and a figure at the
floor (48 by 48) keeps its control inside its own box; and a figure inside a link that holds more than it
(`[![alt](fig.png) caption](other.md)`, an author's `<a>` with a caption beside the img; `linkAbove`: ANY anchor, or
a path link, above `figureAnchor`'s climb, which stops under a link holding text beside the figure; a dead link too,
an anchor the sanitizer or the viewer stripped of its href, and an author's named target with no href, `<a id="fig1">`,
since a control inside one is nested interactive content whatever the anchor's href, and read as `a[href]` the
predicate let a captioned picture inside a dead link wear its control inside the anchor, the file review), since
a button inside a link is the link's click too (one click opened the link's target AND the picture, and put an entry
on the trail the reader never asked for); a figure alone in a link keeps its control, after the link. The clicks (the
body's second click listener, beside the links', since file-view-links.test.ts pins the first listener's text and
order and the two act on disjoint targets): a plain click on the control or on the bare figure opens it as above; a
Cmd/Ctrl-click on a LOCAL picture, where the press reaches the picture (the Comments panel closed, or the pointer
coarse: with the panel open on a fine pointer the layer's overlay below takes the press, modified or not, and offers a
comment, while the control opens at any time; the file review's landing round, fresh-1), opens the kernel's /file URL
in a tab, as a PDF's modified click does (`openFileTab`; a blocked popup falls through to the viewer), and stops
before the row as a link's modified click does; the figure's own click
yields to a figure inside a link (the author's link, through the links listener; and an anchor with an href that listener
leaves to the browser, a web address of the markdown, which carries no class: the browser's own open of the address,
never the picture beside it, the review's round 1; a captioned picture inside a dead link or a named target, an anchor
with no href, wears no control and its plain click opens the picture, that anchor being none of the links the listener
yields to, file-view-figure-shapes-browser.test.ts's dead shape, and the guide's shape sentence says so), to a picture
the panel framed (`panelMark`: the card's), to the
open Comments panel (a plain click is the panel's comment offer, `onImageClick`, and a drag its region; the layer's
overlay takes the press on a fine pointer, and on a coarse one the click reaches the listener and stands down; one
loss stands here, the file review's ui-2, recorded and not built against: a drag that BEGINS inside the control's 22 px
square at the figure's corner draws no region and offers nothing, since the control paints and is hit above the
overlay and takes the press, on a fine pointer alone, while a drag that starts elsewhere and crosses or ends on the
square is unaffected; a stand-down would have the control capture the pointer, read the layer's dragIsClick threshold
on move and hand the gesture to the overlay through a synthetic pointerdown, a coupling between the control and the
layer, open point 5; the guide's figure sentence names the square) and to
a drag that selected and ended on the picture (`selectionOpenIn`). The listener also stands down on a click another
listener already answered (`ev.defaultPrevented`, its first line): the gate listener, first on the body, prevents
default as it restores a placeholder's img, and a click dispatched on that img (a display:none element no pointer
reaches; a synthetic case from a read-only pre-drive, not a measured one) arrived at this listener with the img
restored, was read as a bare figure, and opened its target. Held by file-figure-open.test.ts (the source pins:
the one decision, the target, the two insertion points, the click routing, the walks, the sheets) and
file-figure-open-browser.test.ts (Chromium: the controls on a synthetic report, the hover reveal and the corner in
both float cases, Tab and Enter, the place kept across the open and Back, the plain click with the panel closed, the
modified click's tab, the linked figure, the gated remote figure, the inline data picture, print media, no hover, and
with the panel open the comment offer, the region drag and the control's own click on a fine pointer, and on a coarse
one the tap standing down to the offer, the modified click's tab and the control's open), and, for the round-1 rules,
file-view-figure-shapes.test.ts (the source pins: the web test before the join; the one decision: the state, the
floor, the target and any link above in figureWantsControl's order, decideFigureControl's add or remove against the
control standing, the measure's reads, linkAbove as any anchor, the load, the error and the figures' own ResizeObserver
running it and the width watch's repaint running none, removeFigureControl's order, figureTarget's refusal of both
states, and both sheets' comment naming decideFigureControl; the click's yield to an anchor with an href) and
file-view-figure-shapes-browser.test.ts (Chromium: twelve shapes on one report, a captioned picture inside a dead link
among them, which wear a control and where it
stands, the badge's face and the prose before the icon under the pointer, the plain click on the captioned links, on
the badge and on the two web links, the control of the figure alone in a web link, the protocol-relative figure's
tab from its control and from its click, and the dead link's plain click opening the picture), file-view-figure-floor-browser.test.ts (Chromium: the 761 by 76 figure's
control leaving as the viewport or the Comments aside narrows the column under the floor and returning as it widens,
a page opened at the narrow width with none, a click dispatched on a gated placeholder's img opening nothing
while a real click on the restored figure's control opens its tab, the held picture's re-open, and, since the file
review's round 2, a 1300 by 110 band at a 1200 px modal losing its control at three A- presses (70%, the band's height
under 48 px with the body's width unmoved) and getting it back at three A+, the same by Ctrl + wheel, a control
removed while it holds the keyboard handing it to the viewer's body, PageDown then scrolling the report, and, since
before the file review's round 3, the viewer hidden by display:none at 381 px gaining no control while hidden and the
control following the real box at the show, and, the file review's round 3, a loaded `<img hidden>` and a loaded
`<img width="0">` beside prose getting no control at their load and none at a reflow while the wide figure beside them
wears its, a click on the words before each opening nothing, and a picture re-fetched while the card is hidden losing
its control at that load and getting it back at the show), and, for the chosen candidate,
file-view-figure-chosen.test.ts (the source
pins: chosenSource's body, figureTarget's read of it first, failedSource's delegation and the two callers) and
file-view-figure-chosen-browser.test.ts (Chromium: a `<picture>`, a srcset img and a gated remote `<picture>` open the
candidate shown, through the paint's URL, and the remote figures' requests at a context-level route with the real
window.open, installed with the page's fetch wrapper before the open: none while gated and none at the open, one image
request per remote figure at the gate's lift, one document request per tab from the loaded picture's control, its
plain click and its Ctrl-click, none from the failed remote figure's plain click or Ctrl-click, nothing to any other
host through window.fetch, and the Cookie header of each request with Lax, Strict and None seated), and, for the one
decision, file-view-figure-state-browser.test.ts (Chromium: a failed figure, a
fetching `<picture>` and a srcset figure whose chosen candidate is a `data:` URI, each without a control, the link
beside the failed figure taking the click, the fetching figure's plain click opening nothing and its load bringing the
control that opens the source's file, and a failed local figure with a box, a non-empty alt laid out as text, whose
plain click and Ctrl-click open nothing with the trail unmoved) and, for the door, file-view-figure-recent-browser.test.ts (Chromium over the
real Files page: no Recent row for the picture opened from the control or from the plain click, Back to the report at
the reader's block, a Forward step onto the picture minting its row and Back moving the report's over it, and a
link's open still taking its row).

L4. **The picture view reached from a report.** The control's open is the ordinary open of the picture's path
(openFileView through openFromViewer), so the card shows the picture as `imgBlock` shows any picture, the bar names it
(`.fileview-base`), and Back is enabled with the report's name in its title ("Back to report.md"), L1's push. No zoom
control in this slice: a Fit / 1:1 toggle on the picture view is recorded as a follow-on for the owner (open point 2).
Held by file-figure-open-browser.test.ts (the bar's name and the Back title after Enter on the control).

L5. **Browser history: not integrated.** The trail is the viewer's own: no pushState, no hashchange, no history API
call in file-trail.ts or file-view.ts. A pushState per step would put entries on the joint session history that outlive
the viewer, so the browser's Back after the viewer closes would step through closed files or leave the page, and the
Files pane is an iframe of the dashboard, whose entries join the shell page's history; popping the entries at the close,
and telling the pane's steps from the shell's, is a design of its own. Recorded as a follow-on for the owner with that
trade-off (open point 1); meanwhile the chords take the browser's step while the viewer is up, outside L2's
stand-downs (L2).

L6. **No kernel change, no new route; one new kind of request leaves the machine.** No kernel change and no new
route: a Back or Forward open fetches the file through the same `/file` route the link's open used, a figure's open in
the viewer fetches the picture through it as the report's paint did, and the trail lives in the page. One request is
new (the file review's HIGH 1): a plain click on a loaded remote picture, its Open the picture control, and a
Cmd/Ctrl-click on it open a top-level tab at the picture's address (L3, `openUrlTab`), a second, differently kinded,
credentialed request: a request of type document to a host the page had requested the image from, carrying cookie
classes the image request did not (measured in Chromium by file-view-figure-chosen-browser.test.ts: the Lax and the
None cookie on the tab's document request, the None cookie alone on the image request, the Strict one on neither);
before this follow-on only an author's link opened such a tab. A failed figure opens nothing on any gesture (L3, the
file review's round 2), so the image request has always been made before the tab is asked for; the round-1 wording,
a host the page had already fetched the image from, was false for a failed remote figure (extra5-4). The gate is not
bypassed: no request reaches a host the gate still holds. The build's record here claimed that nothing leaves the machine that did not before, and the PR body and
the contract said the same; the claim was false, and the follow-on is a privacy surface, landing on the owner's word
(open point 11). The verifications: `git diff --stat $(git merge-base origin/main HEAD) HEAD -- kernel/` is empty and
`git diff --name-only $(git merge-base origin/main HEAD) HEAD` lists files under ui/webview, docs, plans, tools,
upstream or tests alone (42 files, the ledger entry's where line; run 2026-09-21 at the head that carries the file
review's landing round's fixes, where the merge-base is the fork's main the branch had merged for the file review's round 5 and the listing is the
branch's whole delta over it; the run at the head after that merge, for the file review's round 5, listed 40, before the
landing round's executed test re-aimed two more standing suites; the two earlier runs, at the commit that built the one
reader for the file review's round 4 and at the head
that closed the author's closing pass after the file review's round 4, listed 38 from the older merge-base they shared,
before the merge made main's tools/markdown-viewer-plan-gate-adopt.test.mjs a file the branch edits;
tools/markdown-viewer-plan-linknav.test.mjs runs both behind the two-part gate the Tests paragraph names, the merge-base
not `origin/main` itself and the diff since it adding the module, reads the count off this sentence where they run, and
otherwise says which part held them, or holds the prose alone without the ref; the Tests paragraph says where that is).
The build's record ran both against 34142c262, the branch point, and the merge of main into the branch
(f694e5974) made that commit an ancestor of main, so at the merged head the same stat named four kernel files and the
same list reached kernel/ and vscode-extension/ (the file review, fresh-1): a verification is derived from the
merge-base with main, never from a fixed sha a merge can move behind. The files under tests are
tests/test_guide_files_failures.py, re-aimed in the review's round 1, and
tests/test_guide_trail_chords_and_figure_button.py, added in its round 2, both named in the Tests paragraph below.

**Tests.** `ls ui/webview/file-trail*.test.ts ui/webview/file-figure-open*.test.ts` lists the follow-on's four
modules: ui/webview/file-trail.test.ts (the pure functions, the chord table, the titles, and the wiring pinned at
source: the one tag, both exits, the reload, the bar and the listener), ui/webview/file-trail-browser.test.ts
(Chromium over the real Files page and a chat-modal page: the contract's cases 1 to 5 and 7),
ui/webview/file-figure-open.test.ts (L3's source pins) and ui/webview/file-figure-open-browser.test.ts (Chromium over
the real chat modal: case 6 and L4). The review's round 1 added two modules outside those two stems:
ui/webview/file-view-figure-shapes.test.ts (the source pins for L3's round-1 rules: figureTarget's web test before
the model's join, the one decision's order in figureWantsControl (the state, the floor, the target, any link above),
the measure's reads, the bare
figure's yield to an anchor with an href) and ui/webview/file-view-figure-shapes-browser.test.ts (Chromium over the
real chat modal: twelve figure shapes on one report, which wear a control and where it stands, the badge's face and
the prose before the icon under the pointer, the plain click on the captioned links, the badge and the web links,
the protocol-relative figure's tab, and the dead link's plain click opening the picture); its round 2 added tests/test_guide_trail_chords_and_figure_button.py (the
guide's two sentences, pinned flattened, held to the lines that make them true: the dashboard shell's ownership of
Alt+Left and Alt+Right to the shell script's listener, onNavKey's stand-downs and navChord's two chord families; the
pictures without the button to the floor's constant, a census of figureWantsControl's refusal arms (an arm added or
removed fails there until the guide's sentence is read again; re-aimed in the file review's round 2 for the failed
picture, which the button and the click refuse on one verdict) and the click listener, and the guide's figure sentence
to the tools pin's copy of it, byte for byte; and, since the file review's round 4, extra8-3, the hide of the Back and
Forward pair, `nav.hidden` in openFileView, asserted in one test with the guide's condition clause and the browser plan's
"(the pair hidden until then)", the two sentences that claim it, and with the tools pins that quote them, so a revert of
the hide along open point 13's road fails there naming the two sentences, rather than a longer list in that point), and,
for figureTarget's read of the candidate the browser chose, ui/webview/file-view-figure-chosen.test.ts (the source pins:
chosenSource's body, figureTarget's order, failedSource's delegation and the two callers) and
ui/webview/file-view-figure-chosen-browser.test.ts (Chromium over the real chat modal: a `<picture>`, a srcset img and a
gated remote `<picture>` open the candidate shown through the paint's URL; since the file review, the remote figures'
request census at a context-level route with the real window.open, and since its round 2 the route and the fetch
wrapper installed before the open, the never-drained list of foreign fetch calls, the Cookie header of each request
with three classes seated, the loaded picture's Ctrl-click and the failed remote figure's clicks). The floor's re-read
at each reflow of the figure and the click listener's stand-down on an answered click added
ui/webview/file-view-figure-floor-browser.test.ts (Chromium over the real chat modal: the 761 by 76 figure's control
leaving as the viewport narrows the column under the floor and returning as it widens, the same across the Comments
aside opening and closing, a page opened at the narrow width with none, a click dispatched on a gated
placeholder's img opening nothing while a real click on the restored figure's control opens its tab, and, since the
file review's round 2, the text-size step by the buttons and by Ctrl + wheel taking a band's control away under the
floor and giving it back at a constant body width, the keyboard handed to the viewer's body when the control
holding it is removed, and, since before its round 3, the hidden viewer's 0 by 0 report adding no control while hidden,
the control following the real box at the show, and, since its round 3, the two authored boxless figures and the load
while hidden) and re-aimed
ui/webview/file-view-figure-shapes.test.ts (the re-read's pins: watchFigureBoxes's body, its 0 by 0 skip with its narrowed
reason and its arming at the paints alone, figureBox's read of the laid-out box as it is for a figure in the document,
the repaint deciding no figure and the width-only re-read gone from the source, removeFigureControl's order, the one rule
figureTarget and figureWantsControl refuse on, figureHasPicture, over FigureState's four values, with each refused
member's literal derived and pinned absent from every other string literal of the file, read as the compiler reads them
through ui/webview/source-units.ts, and both sheets' comment
naming decideFigureControl)
and ui/webview/file-figure-open.test.ts (the stand-down as the listener's first line).
The file review (2026-09-20; the control decided from the figure's current state by one function, and the figure's own
door into the viewer) added ui/webview/file-view-figure-state-browser.test.ts (Chromium over the real chat modal: a failed figure, a
fetching `<picture>` and a srcset figure whose chosen candidate is a `data:` URI, each without a control, the link beside the
failed figure taking the click, the fetching figure's plain click opening nothing and its load bringing the control that
opens the source's file, and since its round 2 a failed local figure with a box whose plain click and Ctrl-click open
nothing) and ui/webview/file-view-figure-recent-browser.test.ts (Chromium over the real Files page: a picture
opened from a figure, by the control and by the plain click, takes no Recent row while Back returns to the report at the
reader's block, a Forward step onto the picture mints its row, and a link's open still takes its row).
Fifteen standing suites were re-aimed, not undone:
ui/webview/file-view-text-size.test.ts (its real-module bar leg at 380, 420, 480 and 600 px in the chat and feed modals
reads the group hidden on a fresh open and, once a link is followed, measures the two glyphs among the actions, case 8), ui/webview/file-view.test.ts and ui/webview/file-view-links.test.ts
(the delegate's open through openFromViewer; the model import), ui/webview/file-view-figure-error.test.ts and
ui/webview/file-view-figure-error-browser.test.ts (the label readers step past the control),
ui/webview/fileview-parity.test.ts (the control's rules byte-equal in both sheets),
ui/webview/anchor-map-fallback-markup.test.ts (the stand-in's control list), and in the review
ui/webview/file-view-notice.test.ts (its Escape cases run every keydown handler an open registers in the document's
order, the capture phase first, since the trail's listener is an open's newest registration, and the close hooks'
removal carries the capture flag its add did), ui/webview/md-url-view.test.ts (the local-file mode's sibling link opens
through openFromViewer with a push, and the door's shape: the tag set, the host's opener called, the tag cleared in a
finally) and tests/test_guide_files_failures.py (both walks' control lists carry fv-figopen, the figure's other
text-free neighbour, as the seventh entry), and in the sweep after the review ui/webview/pdf-new-tab.test.ts (its count
of the gesture reads inside openFileView, which held the links' two, counts the links' two and the figure's four as two
regions and the stretches before, between and after them as none, so a read anywhere else in the function, its own
open's, still fails), and at the merge of the fork's main and in the file review's landing round
ui/webview/file-view-seam.test.ts (its re-parse census: the callee list gained addFigureControls, this follow-on's pass,
with the local functions it reaches, and since the landing round the walk follows a reached local's imported callees and
every import form transitively, judging the sites it finds per module, with the whole file's count in its one home) and
tools/markdown-viewer-plan-gate-adopt.test.mjs (main's pin of the "Fix: the gate before adoption (2026-09-20)" section: its
held copy of that section's re-parse paragraph, re-derived, with the derived figures filled from the seam test's pins), and
in the landing round ui/webview/anchor-map.test.ts (the control at the box's top level is no block's node, executed beside
the failed figure's label's case: the img's html block owns its img alone, or the panel's wrap, the control answers no
block, the paragraph after pairs and paints, and beside prose the caption maps) and
ui/webview/md-config-figure-gate-place.test.ts (readPlace over a loaded figure wearing the control, inside the block's
paragraph and beside its text). The guide's Links in a file paragraph gained two sentences, the trail's and
the figure control's, and the browser plan's navigation-stack section (plans/file-browser.md) a pointer sentence.
tools/markdown-viewer-plan-linknav.test.mjs holds this section to the tree: the section is present once after "## Out of
scope" and carries the ask, what existed, the six decisions, the tests and the open points in that order; the trail
module exists with the functions L1 names and the viewer calls it where L1 and L2 say; the words quoted here and in the
guide are the sources' literals; the sheets carry L3's rules under `screen` in both sheets and the print block names the
control nowhere; no history API call stands in the trail or the viewer; L6's two verifications are run from the
merge-base with `origin/main` behind a two-part gate read off git, the merge-base not `origin/main` itself and the
diff since it adding the module (the file review's round 4, extra8-1: the kernel stat empty, every changed file under
the six directories, and the count L6 gives the listing's, on the open PR branch in a clone where `origin/main` has
moved past the branch's last merge of it; on main, on a batch head cut from main's tip, on this branch right after
merging `origin/main` and on any later branch once the follow-on has landed the checks stand down and the diagnostic
names the part of the gate that held them, and without the ref the prose alone holds; a batch head that main has moved
under passes both parts and fails the count on the other PRs' files, the gate's residual, disclosed in both modules and
here and not closed, a third part named for the maintainer in the PR body: the author's closing pass after the file
review's round 4, attribution-and-gates-2 with records-2; the gate is a pure function over git's answers, pinned in all
four cells, the module's own path asserted to exist in the tree, and the running shape and the three hold-offs run
against a temp repo shaped as the open PR branch, in this module and in the attribution module alike: the file review's
round 5, tests-7, since a hold-off is a pass and a misspelt path would have held the checks off for good behind a green
diagnostic); the guide's two sentences are whole and the old
wording is gone; the browser plan's pointer stands in its navigation-stack section; and the module list is two-way
(every module the listing above produces is named here and the count in that sentence is the listing's, read from the
sentence; every test module under ui/webview, tools or tests whose own text names this follow-on is named here; the
re-aimed sentence's count is the number of pre-existing test modules the diff since the merge-base with `origin/main`
modifies, read from the sentence and compared, with each of them named in that sentence, behind the same two-part gate as
L6's verifications, since a module's own text need not name this follow-on for the branch to have changed it, which is
why the text-keyed rule alone let the count stand short by two (the file review's landing round, tests-3); every
module named here exists, this one included). The three checks keyed on the diff since the merge-base with
`origin/main` (L6's kernel stat and listing, one check with two claims; the re-aimed count's comparison with the
delta; and the attribution module's second road, below; the re-aimed count's list-vs-count half is not among them and
runs in every checkout) run in no checkout that gates landing, and in none after the merge: the fork's CI checks the pull request out at depth 1 in the
jobs that run `node --test tools/*.test.mjs` and `npm test` (no `origin/main` there, so the gate's first part holds them
off; only the secrets job fetches history, and tools/markdown-viewer-plan-linknav.test.mjs holds those two jobs to a
checkout with no `fetch-depth: 0`, so a change there names this sentence), and once the follow-on has landed every later
branch's diff since its merge-base adds that branch's files and not these modules, so the guard that lands is the
attribution module's first road, the rule over the tree, and every claim about the delta, L6's two and the re-aimed
count's comparison, holds by the prose alone, re-derived by hand at the merged head (the file review's round 5, extra5-1 with tests-1, correctness-4 and extra5-3: this
page had stated the gate and the stand-down apart and never composed them, so a reader was never told what the enduring
guard is). tools/markdown-viewer-plan-linknav-review.test.mjs holds the review's
corrections to this record: L3 names the floor by the source's constant and the number the source gives it, its two
exclusions with their functions, the web test's place before the join and the click's yield to an anchor with an href,
the floor's re-read at each reflow of the figure by its function and the click's stand-down on an answered
click, both carried by the source, the decision at the load and the error in place of the paint's add and the load's
drop, linkAbove as any anchor, the tab's document request from the three gestures with the claim's three clauses in
L3 and in L6, the cookie classes the leg measures, the failed figure opening nothing, the hidden group and the drag
that starts on the control, each carried by the source or by a leg; L3 and this paragraph name the two shapes modules and the floor module, which
exist; L6 names tests among the directories and the two files
under it, which this paragraph names too, and derives its verifications from the merge-base.
tools/markdown-viewer-plan-gate-adopt.test.mjs, the pin of the "Fix: the gate before adoption (2026-09-20)" section
above, names this follow-on for one fact about its own section, that it follows "## Out of scope" and is not held to be
the plan's last because this section lands at the same place, and holds that section's re-parse paragraph whole, which
since the merge of the fork's main records this follow-on's two sites in file-view.ts (the bar's trail arrows and the
figure control's glyph) within the whole file's count, and since the file review's landing round the census widened
through this follow-on's pass, addFigureControls, with the modules it reaches and the sites judged there, the derived
figures filled from file-view-seam.test.ts's pins.
ui/webview/linknav-records-attribution.test.ts holds the rounds every record of this follow-on names to the convention in
this section's opening paragraph (the file review's round 3, tests-2, re-ruled onto the structural rule in its round 4,
rules-1, after a pin keyed on one string missed the misattribution in the commits that built it: a round belongs to the
review named nearest before it in its unit of text and is one the convention enumerates for that review; a pass of the
author's has no rounds; an id of the author's family stands only where the review named nearest before it is the author's
pass; a round with no review named fails), reading in every checkout, as a rule over the tree, every file git lists at the repo root, tracked or untracked
and not ignored, whose text names the file review, names the author's closing pass, or carries an id of the author's
family, together with the files the branch created (an existence roster, each judged in full, every unit of it) and this
section, the guide's paragraph and
the browser plan's pointer (judged in full), a phrase outside those judged only where the review named nearest before it
is the file review or the author's pass, so another review's round in the shared file-view.ts, or in a file another PR
brought in, is left alone and counted in the diagnostic (the file review's round 5, extra5-1 with tests-1, and
regression-2: the first road had read a roster of eighteen files, checked against the diff only by the second road, which
runs in no CI job, and had judged file-view.ts's units naming any review's round against this follow-on's enumeration; the
key is the words "file review", the feature's name as well as this review's, so a record of another review that calls
itself the file review, or a sentence about the file-review feature followed by a round, is judged against this
enumeration and reds the module until that review takes a qualified name or the key is extended, no such unit standing at
the swept head, and outside the created files a round naming no review is counted and not faulted, the diagnostic printing
where it stands; the author's closing pass after the file review's round 5, tree-2 and reader-6),
a new uncommitted file among the population (correctness-5 with tests-6: the second road's diff lists tracked paths
alone, so a phrase planted in a new file was a false green), and the count of this follow-on's units in file-view.ts held
equal to the derived count at the swept head (correctness-6 with tests-5 and extra8-4: a floor of ten had stood against
fourteen); and, kept and disclosed above (it runs in no CI job and in none after the merge), every unit the branch added
or touched since the merge-base behind the same two-part gate (the merge-base not `origin/main` itself and the diff
adding the module; the file review's round 4, extra8-1: before the gate the roster equality would have failed every later
branch in the repo once the follow-on landed, and a gate on the module's presence alone would have passed a batch head),
the diff's added files printed beside the created files there for a human to compare. It and ui/webview/file-view-figure-shapes.test.ts read TS and JS through
ui/webview/source-units.ts, the compiler's parser (comments as text with wrapped lines joined; each string the program
sees as one value as one unit with that value, in either quote, escapes resolved, a `+` chain of literals folded into the
value it computes and a template's spans joined with each hole kept as its source text, so a phrase split across tokens
is judged whole; a join, a concat and a hole's run-time value outside the read, which the reader's header lists), Markdown
as paragraphs and Python as paragraphs with its string literals cooked as Python cooks them and adjacent literals glued,
the file's suffix picking the reader and a suffix the reader has no rule for refused naming the file rather than read as
prose (the file review's round 5, correctness-7 with tests-4 and extra7-2: .tsx, .jsx and .cts had fallen through to the
prose arm with no word to the caller; the tree road's diagnostic lists the suffixes it read),
every unit charging a phrase to its source line through a starts map built from source positions (the file review's
round 5, correctness-2 with extra6-1 and tests-2, extra6-3, and correctness-1 with tests-3 and extra7-1: the reader had
emitted one unit per literal token, so a phrase split across a `+`, a hole, Python's adjacent literals or an f-string
field sat in no unit; had built the starts map from the cooked text's newlines, charging an escaped-newline literal's
fault to lines past it, which an added-line filter then dropped; and had dropped every backslash of a Python escape, so
`\n` read as the letter n): the one reader for both pins, since the file review's round 4 ruled that a guard against a form is
keyed on the property or parses, and that three guards keyed on three spellings are fixed as one mechanism. The author's
closing pass after the file review's round 4 stated each pin's boundary in its message and pinned it by execution (guards-1
with records-11: the refused-state pin reads whole literal values and regular expressions, not an identifier key, a word
assembled at run time, a prefix or a case-folded test; guards-2 with attribution-and-gates-3: the attribution pin reads a round as
`round` or `rounds` followed by digits, a comma list or a `to` range after `rounds` as the set, and no ordinal, spelled-out
or abbreviated form, and an id as the family word, a hyphen and digits), had the attribution pin's second road diff the
working tree against the merge-base so an uncommitted planted phrase is charged like a committed one (guards-3), charged a
fault in this section to its plan line rather than a section-relative one (attribution-and-gates-4), and widened its first
road's read of file-view.ts to the units carrying an id of the author's family beside those naming the file review (the
same closing pass, records-1); since the tree rule of the file review's round 5 that read is keyed on the review named, so
a pass misnamed as a round beside its id is judged there where the pass is named nearest before the round, while a round
beside an id with no review named, or the branch's review named with a round over 2 beside an id, is counted and left
alone in that shared file, judged in full only inside the created files and the three records (the author's closing pass
after the file review's round 5, tree-1, correcting the earlier form of this sentence, which said every such comment is
judged in every checkout). The census
those two pins grew out of, every line the branch added since the merge-base 3711863c9 that names a review, run for the
file review's round 3, tests-2, with the corrections it produced: the commit that recorded it said 173 lines over 19
files at this head, and 173 is the count at that commit's parent, 677b0e1c8; at the commit's own head, 2a35d92c9, the same
definition gives 178 lines over the same 19 files, the five more being the lines that commit itself added, each naming
its review rightly (the file review's round 4, tests-4; both counts re-derived on 2026-09-20 by the census script kept
beside the contract, run in a detached copy at each of the two heads; the commit's message stands as pushed, since
amending it would move every later commit).
tests/test_file_view_bar_browser.py, the served bar pins, read the groups
inside `.fileview-acts`, and the nav group stands outside it, in the bar itself, before the path; run as a single module
at the records commit, green (`pytest tests/test_file_view_bar_browser.py`, a run that needs the extension deps and a
Playwright browser).

**Open points for the owner.**

1. Browser history. The trail is the viewer's own (L5). Integrating it (a pushState per step, popped at the close, the
   Files pane's iframe told from the shell) would give the browser's Back and a back-swipe the trail's meaning, and
   Alt+Left too outside the dashboard, whose shell takes the key first (open point 10); the cost is entries that
   outlive the viewer and a design for the pane's frame. A ruling on whether to design it.
2. A Fit / 1:1 toggle on the picture view (L4): a picture reached from a report shows as imgBlock shows any picture,
   shrunk to the card, with no zoom.
3. The trail across a close (L1). Closing the viewer ends it; the alternative keeps it for the page's life so a reopen
   of the same file from Recent finds its Back again. The choice is a ruling; the code's end is one line in
   closeFileView.
4. An outside open of the file already shown roots the trail (a chat pill for the file the viewer shows drops its
   Back), the contract's literal rule; widening L1's same-file keep to untagged opens is a ruling.
5. With the Comments panel open, a region drag cannot START inside the control's 22px square at the figure's corner
   (the control is hit above the overlay); a drag that starts elsewhere and crosses or ends on it is unaffected, and
   the loss is a fine pointer's alone (no overlay and no drag on a coarse one). Recorded in L3 and in the guide's
   figure sentence (the file review's ui-2); the stand-down, the control handing a press that becomes a drag to the
   layer at its dragIsClick threshold, was not built: it needs a pointer-capture transfer between the control and the
   layer. Whether to build it or to leave the record as it stands is a ruling.
6. Not measured here. Only Chromium (Playwright, Linux) measured the layout, the click routing and the chords; Cmd+[
   and Cmd+] are held by the pure chord table alone, and Cmd-click was exercised as Ctrl-click; the embed chip
   (`![[Note]]`) the contract lists among the pushes was not driven, the wikilink (`[[Note]]`) was; the Waiting pane's
   links and the file browser's rows are outside by construction (no tag) and were not driven, the Files pane's relay
   and Recent rows were; desktop Firefox and Safari were not run.
7. Discoverability. On a hover-capable device the control is transparent until the pointer is over the picture or the
   button holds the focus; the plain click on the picture is the other door, and the guide says so. Whether the control
   should show at rest is a ruling.
8. The plan's two follow-on sections. The print follow-on (branch filereview-print, in flight) appends its section at
   the same place, after "## Out of scope", and its pin requires its section to be the plan's last; this section's pin
   requires only that it follows "## Out of scope", so when both land this section goes before the print one.
9. The chords' stand-downs (L2). With a text field focused, or the editor open and the focus on a bar button, Alt+Left
   is the browser's Back on Linux (verified) and, by the same accelerator, Windows, and leaves the page under the open
   viewer, an unsaved edit with it. Whether `onNavKey` should take the default there too and step nothing (the viewer up
   and the caret outside the editor's own field; CodeMirror keeps its own Alt+Left), or a beforeunload guard should hold
   a dirty editor, is a ruling: the first trades a field's own Alt+Left (the caret's word step on a Mac) for the page's
   safety.
10. The chords inside the dashboard shell (L2). The shell's pane-focus script takes Alt+Left and Alt+Right first on
    every pane document as the move between panes, so in a shell pane the arrow chords never reach the trail and only
    the Mac's Cmd+[ and Cmd+] and the buttons step it; read from the listeners' order, not driven. Whether the shell
    should yield the arrows to a pane whose document has a viewer up (`#romp-fileview`), or the trail's arrow chords
    should be other keys, is a ruling; the guide's trail sentence states the exception (the review's round 2, held by
    tests/test_guide_trail_chords_and_figure_button.py to the shell script's lines).
11. The remote picture's tab (L3, L6; the file review's HIGH 1). Two roads, both priced here and neither chosen: (a) as
    built: a plain click on a loaded remote picture, its control, and a Cmd/Ctrl-click on it open a top-level tab at
    the picture's address, a document request to a host the page had requested the image from that carries cookie
    classes the image request did not (L3's table), where before the follow-on only an author's link did; one gesture
    opens every picture, remote or local, and the tab is observed as a request by
    file-view-figure-chosen-browser.test.ts from each of the three gestures; (b) the narrow road: the tab for the
    explicit control and for a Cmd/Ctrl-click alone, a bare plain click on a remote picture doing nothing, as before
    the follow-on. The narrow road keeps the request: the control and the modified click still open the same
    credentialed tab (the file review's round 2, extra5-3), so it changes which gesture makes it and not what leaves;
    the cost is one gesture meaning two things by where the picture comes from, and the change is a flag on
    openFigure's call from the control's branch that the web arm reads beside `wantsOwnTab`, with the plain-click case
    of three browser legs re-aimed (file-view-figure-chosen-browser.test.ts's plain-click tab,
    file-view-figure-shapes-browser.test.ts's protocol-relative figure, file-figure-open-browser.test.ts's remote
    picture) and the guide's "a picture from the web opens its address in a new tab" narrowed to the button and the
    modified click. A failed remote figure opens no tab on either road (L3). The reviewer's reading
    (romp-manager, 2026-09-20), for the owner to take or leave: the explicit control is an unambiguous gesture and a
    plain click on a picture is not, so a plain click opening a credentialed third-party tab is the surprising one. The
    landing is the owner's whatever the tier.
12. A picture opened from a figure takes no Recent row (L3): the default taken, so the report's row stands and Back
    reaches the report through the trail. With one exception, L2's rule, stated here because the default is ruled on
    here (the file review's round 2, extra8-1): a Back or Forward open is the pane's own (openFromViewer through the
    host's opener, files.ts openHere), so a Forward step onto the picture puts its row at the head of Recent, and the
    next Back moves the report's row back over it; file-view-figure-recent-browser.test.ts drives
    the composition (the figure's open, Back, Forward, Back). The eviction the default guards against cannot return
    through it: a picture opened from a figure is a leaf of the trail (the picture view has no link to follow), so it
    stands ahead only until the next push, which clears the list ahead. The alternative, a row for the picture as for
    any file the pane's opener opens, is the host's opener in place of the figure's door (openFromViewer's push in
    openFigure, the trail kept, the row minted by files.ts openHere); a ruling, and
    file-view-figure-recent-browser.test.ts inverts with it. Closing the exception instead, no row on a Forward step
    to a figure-reached picture, is not a one-line change: TrailEntry carries no field that tells a figure-opened entry
    from a link-opened one, and routing the step through openFigureInViewer would push, clearing the list ahead.
13. The Back and Forward pair hidden on an open with no step either way (L2): the file review's ruling (round 1,
    ui-1; re-decided in round 2 on T367, extra8-2), built in the round-2 fixes against the contract's L2 clause, which
    had the pair dimmed, and the contract corrected with it. The hide reclaims about 74 px of a 359 px bar at a 380 px
    viewport and moves the file name 74 px on the first link follow of every trail (the file review's measurement).
    If the contract's dimmed pair is wanted back: the one `nav.hidden` line in openFileView goes, and the pins and legs
    L2 names invert (file-trail.test.ts, tools/markdown-viewer-plan-linknav-review.test.mjs,
    file-trail-browser.test.ts, file-view-text-size.test.ts's bar case).
