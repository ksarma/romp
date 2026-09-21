---
title: The chat renderer keeps a path's underscores literal: no emphasis delimiter opens or closes inside a token the path walk would link
status: candidate
where: ui/webview/md-config.ts (pathAwareEmphasis, an emStrong tokenizer override exported beside mdExtensions and not in that list; its helpers linkableRuns (now taking the parse's lexer and the masked string), tokenAt, proseRun, shiftedEscapes and flankedInside (the wholeness test by code point), the constants DRY_LEXER, HIDDEN and FLANKING_RE (the emphasis spec's flanking class, stated in the override's own words), the type LinkableRuns and the linkableMemos WeakMap (one memo per lexer; MEMO_SLOTS and the linkableMemo list are gone); the boundary list in its comments, with the class with two faces stated at the rule level and the constructs clause; the mdExtensions docstring); ui/webview/chat-md.ts (chatMarked beside userMarked, both taking the override; chatMdHtml); ui/webview/render.ts (md() parses through chatMdHtml; the chat-md import and the grammar comment above the singleton; userMd's comment); ui/webview/path-links.ts (trailingPunct exported); ui/webview/md-emphasis-paths.test.ts (new; twelve tests: the chat renders every member row literal, every other row is byte-identical to the base grammar, the adversarial rows change only where the note says, the user's own words take the same grammar, the chat's walk links every wanted token whole, the base grammar cuts every member row's token, a footnote reference inside a refused pair is numbered once, a file URI and the block contexts are protected too, the instance boundary, the instance boundary as a census over the tree (MARKED_IMPORTERS, eleven modules), THE RULE by execution with a stub in path-links.ts's place (stubBuild), the bare-name gate's live values over BARE_FILE_EXTS); ui/webview/md-emphasis-override.test.ts (new in review round 1; six tests: a pair whose body holds a path with an unbalanced interior run keeps its emphasis, the shapes around it stand, the dry-run stand-in is rules and lexer with the lexer's reads recorded too, the override reads no punctuation class from marked so a memo entry depends on the masked string alone, no extension the chat's instances take overrides emStrong besides pathAwareEmphasis, the override costs at most a few times the base grammar); ui/webview/md-emphasis-atomic.test.ts (new in review round 2; six tests: a linkable token with a run inside it beside a character that can flank a delimiter run is one word whole (the WHOLE rows, the CODE_POINT rows read by code point and the NOT_WHOLE controls), a plain token keeps the edge rule and its FACES (the widening face's three rows among them), a backslash before an astral symbol masks three UTF-16 units as two, an escaped astral symbol inside a link, a reflink, a code span or a tag counts for nothing, one scan of the paragraph per masked string per parse, the override costs at most a few times the base grammar on a 20 KB paragraph of each shape with the thrashing shape among its rows); the stand-ins re-aimed at the chat's own instance in the 2026-09-21 review, each with an executed pin that a path's underscores stay literal through it: ui/webview/md-sanitize-chat-links-browser.test.ts, ui/webview/md-sanitize-chat-fragment-browser.test.ts, ui/webview/md-sanitize-chat-modified-click-browser.test.ts and ui/webview/md-sanitize-chat-schemeless-browser.test.ts (each probe's __mdProbe renders chatMdHtml; schemeless keeps applyMdConfig for the chrome's viewer), ui/webview/md-sanitize-postpass-browser.test.ts (md, markedOnly, twice and registry on the chat instance), ui/webview/md-config-math-inks-browser.test.ts (__md on chatMdHtml), ui/webview/md-sanitize-katex-browser.test.ts (the local assistant instance replaced by chatMdHtml), ui/webview/md-config-chat-styles-browser.test.ts (split: __md on chatMdHtml for the reply and notice roots, __viewerMd on the singleton for the fileview-md roots), ui/webview/pr-links.test.ts (the bare local chatMarked replaced by the import of chatMdHtml), ui/webview/md-wiki.test.ts (the reply rendered through chatMdHtml); prose corrections in ui/webview/file-view-links.test.ts and ui/webview/fileview-parity.test.ts (the singleton is the hover preview's and the anchor map's; the chat's instances take the list plus pathAwareEmphasis) and in vscode-extension/src/md-strikethrough.test.ts (its header names the viewer's singleton and the chat's two instances); the census pin tools/file-review-viewer-recipe.test.mjs (the header's lists of browser modules spelling the singleton probe moved with the re-aims: 4 modules, all boxed); the dated pointers plans/file-review.md (decision 52: chatMdHtml as md()'s parse since 2026-09-19, after the dated record) and plans/markdown-viewer.md (item 1 of the Slice 4 build note), the former pinned by tools/file-review-plan-inlinetag.test.mjs beside its code pin; six re-aimed source pins: ui/webview/chat-md.test.ts (the singleton stays breaks:false; the local named singletonHtml for what it configures, and the equivalence test compares userMdHtml against chatMdHtml with a path row), ui/webview/md-literal-tags.test.ts (source: one rule, two callers; its message on the singleton's grammar corrected), ui/webview/md-config.test.ts (source: who applies the one configuration; the parity control's title names the singleton), ui/webview/render-math.test.ts (render.ts wires the math extensions into marked), ui/webview/render-sanitize.test.ts (md() sanitizes marked output with DOMPurify, and its CHAT read of chat-md.ts), tools/file-review-plan-inlinetag.test.mjs (md-literal-tags.ts exports the function and the void list; the decision 52 record and its dated pointer); tests/test_file_preview_browser.py (ServedFilePreview._boot's lab, the hover test test_a_hover_previews_the_file_or_its_section_after_the_dwell_and_a_refused_path_is_text_with_no_request, the DRIVER string's link wait and PARK, the module docstring, which names the population note as a note kept outside the repo); comments only: ui/webview/md-literal-tags.ts (the one-rule-one-code-path comment) and ui/webview/file-view.ts (the viewerHtml docstring and mdBlock's comment). Upstream-facing: path-links.ts, render.ts and chat-md.ts (upstream's holds chatMdExtensions and userMarked) exist upstream, as do kernel/kernel.py's _path_tokens and _path_links, file-view.ts, and of the test files chat-md.test.ts, file-view-links.test.ts, fileview-parity.test.ts, pr-links.test.ts, md-wiki.test.ts, render-math.test.ts, render-sanitize.test.ts, md-sanitize-chat-fragment-browser.test.ts, md-sanitize-postpass-browser.test.ts, md-strikethrough.test.ts and tests/test_file_preview_browser.py (each present on upstream main, checked 2026-09-21); fork-only: md-config.ts, the module the override lives in, with md-config.test.ts and the three md-emphasis test modules; md-literal-tags.ts and md-literal-tags.test.ts; the probes md-sanitize-chat-links-browser.test.ts, md-sanitize-chat-modified-click-browser.test.ts, md-sanitize-chat-schemeless-browser.test.ts, md-sanitize-katex-browser.test.ts, md-config-chat-styles-browser.test.ts and md-config-math-inks-browser.test.ts; plans/ and tools/ (the viewer project's); upstream/2026-09-19-md-emphasis-paths.md (this entry: the record itself, named because the ledger's where-check lists every file the diff touches, the entry included)
added: 2026-09-19
pr: 869
tier: fix
offered:
closed:
---
Reproduction credit: romp-upstream's browser census (browser-flake/census-2026-09-19.md, Entry 5, a note kept outside the repo) read one CI failure of tests/test_file_preview_browser.py to its mechanism: the lab's random temp name began with an underscore and a later segment ended with one, CommonMark's flanking rules made the pair an emphasis, the chat rendered the outside path's middle as em, and the link walk never saw the token whole (about 3 in 37 squared per run; the test was a bystander). The derivation is md-emphasis-population.md (a note kept outside the repo; 55 rows and 20 adversarial rows, each measured against marked 12.0.2, the CommonMark reference implementation, the chat's walk and the kernel's tokeniser): marked is spec-correct on every row, so the class is the chat's road, which renders a reply as prose markdown over text the kernel has already tokenised as a path, and the fix is an emStrong override on the chat's marked instances that hides a `_` run lying strictly inside a token the walk's scanner and gates would link (the bare-filename gate included, so a bare name in prose is protected and still not linked) from the built-in's closer scan, and refuses an opener, or a spent closer run, lying strictly inside such a token, so a prose pair spanning a path keeps its emphasis around the literal path; a token holding a `_` run inside it beside a character that can flank a delimiter run (punctuation or a symbol, read by code point) is one word whole, its edge runs included, while a plain token's edge run pairs as the spec says (review round 2; the class stated in the spec's terms and read by code point, the 2026-09-21 review). Measured: exactly the 20 member rows change, every one to the literal token, none of the other 35; of the adversarial rows only A08 (emphasis glued to a path with no space between, the accepted loss), A12, A14 and A20. Boundaries: a glob (src/*.py) is outside the linkifier's grammar and renders as before; the singleton (the viewer, the hover preview, the anchor map) keeps GitHub's rendering, as do the feed's notice cards on a bare instance of their own (feed.ts noticeMarked, which links no paths), and whether the viewer's own walk (file-view-links.ts) should follow is a separate decision. Two parity follow-ups stand outside this class, both from the kernel tokenising the raw markdown while the client tokenises the rendered DOM: a path wrapped in markup gives the kernel a key the DOM never shows, and a hand-escaped path is one token to the DOM and three to the kernel.

## How the override decides

pathAwareEmphasis (md-config.ts) is an emStrong tokenizer override. The built-in decides the pair on a dry stand-in
whose lexer lexes nothing, over a masked string in which every `_` run lying strictly inside a linkable token is hidden
from its closer scan, so a prose pair spanning a path keeps its emphasis around the literal path. A token holding a `_`
run inside it beside a character that can flank a delimiter run is one word whole, its edge runs hidden and refused with
the rest (review round 2: an edge run left visible paired across the hidden middle with a partner outside the token),
while a plain token's edge run pairs as the spec says. An opener, or a spent closer run, that is a path's is refused,
the opener before any scan. Linkable is the walk's own scanner, trailing-punctuation trim and shape gates, all imported
from path-links.ts and never restated. The wholeness test keys on the property it needs and reads the neighbour by code
point: a `_` run strictly inside a linkable token makes the token whole when a character beside it can flank a delimiter
run under CommonMark 0.31.2 section 6.2, that is Unicode whitespace, a Unicode punctuation character (general category
P) or a Unicode symbol (category S), `*` and `_` included and letters, digits and lone surrogates excluded (md-config.ts
FLANKING_RE and flankedInside; the pair before the run is read only when both surrogate halves are present). Marked's
punctuation rule, written for the one code unit before an opener with the delimiters excluded by construction, is no
longer read: the 2026-09-20 review's head asked it, and the rule had two holes, both the failure it was added to stop
(an interior run whose only neighbour was a `*`, which the URI arm admits, and one whose neighbour was an astral
punctuation mark or symbol, a lone surrogate to a one-unit read, left the token un-whole and cut from its edge; the
2026-09-21 review, A). The class is the emphasis spec's and not the path grammar's, so stating it restates nothing of
the walk's grammar. A star run falls through to the built-in. The paragraph is scanned once per masked string per parse
and remembered in a memo that lives with the parse's lexer (linkableMemos, a WeakMap keyed by the lexer marked builds
for each parse() call, then a Map keyed by masked string), so the nested lexes of a link's label or a star or tilde
pair's body take an entry beside the paragraph's and evict nothing, whatever their number, and a second parse of the
same text scans once more. The 2026-09-20 review shipped a module-global eight-slot most-recently-used list instead
(MEMO_SLOTS, gone): eight distinct nested strings holding a `_` run between two of the paragraph's delimiters evicted
the paragraph's entry, and every later prose delimiter rescanned the whole paragraph, a term quadratic in its length
where the base grammar is linear, which none of the eleven pinned cost shapes could reach. The 2026-09-21 review derived
the worst case, a 20 KB paragraph of eight distinct `*` bodies between every two prose underscores, at 13.8 to 16.9
times the base grammar with 571 rescans (five runs at load 13; 20.6 to 31.8 in the round's own runs at loads 10 to 21),
doubling per doubling of length, against the tests' bound of four; the algorithm was fixed rather than the bound moved,
since no constant bounds a term that doubles. With the per-parse memo the same paragraph is scanned once at 0.8 to 1.1
times the base (loads 6 to 31), the eleven shipped shapes 0.67 to 1.65, the worst the whitespace-free path run. The
bound of four the tests assert was chosen, not derived: a round number with headroom for a loaded box over the measured
worst shape (that path run, 1.4 to 1.7 at loads 6 to 33), never timed against a shape that could violate it before this
round; it stands now because the cost is linear, and the tests' comments say so. A run's position counts the escaped
astral symbols the mask shortens, read at the masked string's `++` positions off the tail; an escape inside a link, a
reflink, a code span or a tag counts for nothing, since marked masks those to letters before its escape rule runs (the
closing pass; round 2 counted every escape in the tail). In render.ts only md() changes road: the singleton, the viewer,
the hover preview and the anchor map are untouched.

## Boundaries against main

Each row was measured on main's chat road (the singleton after applyMdConfig, and its userMdHtml, which agree on every
row) and at the head in the review's closing pass; the class paragraph and the constructs clause below were measured in
the 2026-09-21 review over a git archive of the reviewed head, through both grammars and the walk. The list of rows that
follows them is the rows measured in the review that render differently from main by this rule: a sample of the class
and of the edge rule's recorded faces, not a derived whole, so the class statement, and not the list, is the record of
what can differ.

The cost of making a token whole is a class with two faces, stated once at the rule level for every token either rule
makes whole (the path and URI arms, and the bare-name gate; the 2026-09-21 review, 106 rows): a `_` run inside a whole
token is hidden, so the run the spec paired it with is left without its partner. LOSS: the pair the spec made is gone,
the token's own (`the _final_.pdf file` renders literal where the spec emphasised `final`; 54 rows) or a prose run's
with a run inside the token (`_see drafts/a_.md now` renders literal where the spec gave `<em>see drafts/a</em>.md now`;
15 rows). WIDENING: when another prose run stands past the token, the surviving prose run re-pairs across it and the
chat emphasises a span the writer never marked: `_see drafts/a_.md and old_ now` renders `<em>see drafts/a_.md and
old</em> now` where main gave `<em>see drafts/a</em>.md and old_ now`, and backward, `_see x-_y.md now_` renders
`<em>see x-_y.md now</em>` where main gave `_see x-<em>y.md now</em>` (17 rows, 11 forward and 6 backward; the www
autolink row below is one of them). A widening can spend a plain token's end-edge run (`_see final_.pdf and /tmp/x_ now`
renders `<em>see final_.pdf and /tmp/x</em> now`, and the link main showed for `/tmp/x_` is gone) and with double runs
changes the pair's kind (`__see final_.pdf and old__ now` renders strong). On the path and URI arms the token is linked
whole in exchange (`drafts/a_.md` links at the head and not on main; `file:///x/a_/b.md` links whole where main linked
the cut piece `/x/a`); on the bare-name arm in prose nothing is linked on either tree, so there both faces are pure
cost. The other 20 rows are identical to main: no prose run reaches a run inside the token, and the control extension
`.zzz`, which no gate admits, is identical throughout. The loss face costs the writer's emphasis, which the change
disclosed from the start; the widening face emphasises text the writer did not mark, the worse of the two, and the
reason the class is recorded whole. Pinned as they render on both chat renderers with the walk's links: the loss face in
md-emphasis-atomic.test.ts's WHOLE table (`_the _final_.pdf file_`) and the widening face in its FACES (the forward,
backward and spending rows above). No frequency over replies is claimed: the one corpus rendered whole through both
grammars, the repo's 48 markdown files under docs/ and plans/ (27,685 source lines, 27,004 rendered lines compared line
by line), has no differing line, since it backticks its paths; a control file holding a member row and a widening row
showed 2 differing lines through the same harness.

The chat grammar's own constructs show the member rule and the two faces and nothing new (39 rows measured in the
2026-09-21 review, 28 differing from main, no boundary of their own): a path inside a mark's, a strikethrough's, a
strong's, a callout's or a footnote definition's body renders literal as in prose and the construct parses on both trees
(`==see /a-_b/c_/d.md==` renders `<mark>see /a-_b/c_/d.md</mark>` where main rendered `<mark>see
/a-<em>b/c</em>/d.md</mark>`; C52 in md-emphasis-paths.test.ts, `see *a-_b/c_/d.md* now`, is the tabled instance), and
any inline construct whose delimiters main's cut straddled, a prose opener paired into a closer-only path inside
`==..==`, `[[..]]`, `![[..]]`, `$..$`, `~~..~~` or `*..*`, now parses whole inside the prose pair or beside a literal
opener (`_see ==drafts/a_.md== now_` renders `<em>see <mark>drafts/a_.md</mark> now</em>` where main rendered `<em>see
==drafts/a</em>.md== now_`; `_see [[drafts/a_.md]] now_` the same with the wikilink's span in place of the mark): the
widening and loss faces with the construct a bystander. A wikilink's target and a formula's text are never inline-lexed
and render the same on both trees; `**` shows no straddle on main, since marked's closer scan skips a `_` inside a `**`
pair; `^[..]` is no construct of this grammar, its brackets literal text on both trees, and is dropped. These are
entailed consequences of the member rule, so they take no row of their own below; the same clause stands in
md-config.ts's boundary list.

The rows measured in the review that render differently from main:

- The accepted loss A08, `_foo_-bar/baz.md`: main `<em>foo</em>-bar/baz.md`, the head literal and linked whole.
- Its `~~` glue, `__note/a.md__~~x.py~~`: main `<strong>note/a.md</strong><del>x.py</del>`, the head
  `__note/a.md__<del>x.py</del>`, linked on neither.
- A plain token's end-edge closer longer than the pair spends, `_see /tmp/x__`: main `<em>see /tmp/x</em>_`, the head
  literal with `/tmp/x__` linked under the kernel's key.
- The URI arm glued to a mask or to punctuation: `file:///x/y.md[link](u)_bar_` (main `<em>bar</em>` after the link,
  the head `_bar_`) and `see file:///x/y.md._draft_ now` (main `file:///x/y.md.<em>draft</em>`, the head literal).
- The www autolink, `_see www.x.co/a_/b.md now_`: main cut the URL at its underscore,
  `<em>see <a>www.x.co/a</a></em>/b.md now_`; the head renders one emphasis around the whole autolinked URL: the widening
  face of the class above, on a token linked on neither tree.
- A path in a link's label, `[see /a-_b/c_/d.md](u)`: main's label `see /a-<em>b/c</em>/d.md`, the head's
  `see /a-_b/c_/d.md`; the walk links under an `<a>` on neither.
- The glossary term walk's result inside a literal filename, `the package's __init__.py imports __main__.py` with `init`
  and `main` as coined terms: main rendered `<strong>init</strong>.py` and the walk linked both terms; the head renders
  the names literal and links neither, by the walk's own no-link-zone rule.

Identical to main:

- The URI arm's class (path-links.ts CLICKABLE_PATH_RE, unchanged on this branch and equal to kernel.py
  _PATH_TOKEN_RE's URI arm): `see file:///x/y.md.draft now` is literal on both.
- Escapes as `++` in the mask: `see /a\-_b/c.md and x_ ok` renders `see /a-<em>b/c.md and x</em> ok` and
  `a-_b/c_/d\.md` renders `a-<em>b/c</em>/d.md` on both.
- The queued twin's LINE (render.ts renderQueued, outside the change's three render.ts hunks) is untouched, AND the
  queued copy of the user's bubble renders through userMd, on userMarked, which takes the override, so every row that
  changes above changes there too, with no path walk on the queued copy (there was none on main either: the gap between
  the queued copy, never walked, and the landed bubble, walked, predates this change and is no new asymmetry). The line
  is identical; the rendering is not.
- The wrapped path `see _docs/x_/notes.md_ now`: `see <em>docs/x</em>/notes.md_ now` on both.
- The plain token's edge rule rows: `_see /tmp/x_` (`<em>see /tmp/x</em>`), `_x/y.md and more_`
  (`<em>x/y.md and more</em>`) and `_see _posts/x.md now_` (`_see <em>posts/x.md now</em>`), each on both.

The round 2 commit's body called the label item, the URI arm's rendering and the glossary result identical on main,
which they are not: this list and the code's boundary list (the boundaries comment in md-config.ts) are the record.

## Tests

md-emphasis-paths.test.ts (new; twelve tests) runs the 55 rows and the 20 adversarial rows through both chat renderers,
the walk over the rendered DOM with the kernel's map, the base grammar's cut, the footnote count, the block contexts, a
file URI, the instance boundary and the feed's bare instance. Since the 2026-09-21 review it also pins the instance
boundary as a census over the tree (exactly eleven product modules under ui/webview import marked, `import type`
accepted and whole files read, each named with the instance it renders or lexes on; a twelfth importer added in a
scratch copy of the tree goes red by name), THE RULE by execution (md-config.ts bundled at test time with a stub in
path-links.ts's place: with every gate refusing, or the scanner yielding no token, every row of both tables renders as
the base grammar does; with a bare gate admitting `.zzz` alone, `the _final_.zzz file` turns literal while `the
_final_.pdf file` keeps its emphasis; the unstubbed bundle renders every member row as the shipped chat does; a
bare-name grammar of the override's own under a spelling the old five-spelling source check does not name, blind to that
check and to every table, reds it), and the bare-name gate's live values (`the _final_.<ext> file` renders literal
exactly when the imported gates admit the token the scanner and the trim derive from it, over every member of
BARE_FILE_EXTS and six non-members, both sets asserted non-empty); the five-spelling source check stays as a secondary
guard with its message narrowed to what it sees.

md-emphasis-override.test.ts (new in review round 1; six tests) pins that a pair spanning a path with an unbalanced
interior run keeps its emphasis on both chat renderers, the shapes around it, the stand-in's contract by a recording
proxy at both levels since the 2026-09-21 review (the reads of `this` and, from the stand-in's lexer, the faked half
with one member, exactly inlineTokens; a built-in wrapped in a scratch copy to read another lexer member reds the pin by
that member's name where the one-level proxy stayed green; the pin records what the installed marked reads and cannot
know what a later version would), that the override reads no punctuation class from marked so a memo entry depends on
the masked string alone (marked 12.0.2's inline grammars share one punctuation RegExp, asserted; a throwaway instance
whose lexer carries a whitespace-only class renders `_see __init__.py now_` as the chat does, whichever renders first;
red over a git archive of the reviewed head, where the chat took the throwaway's entry from the shared list), the
emStrong chain, and the cost ratios against the base grammar on three shapes under the bound of four.

md-emphasis-atomic.test.ts (new in review round 2; six tests) pins that a token with a run inside it beside a character
that can flank a delimiter run is one word whole on both chat renderers and the walk links it under the kernel's key:
round 2's 24 rows and, since the 2026-09-21 review, 23 URI-arm rows read by code point (a `*` beside the run, in either
order and with a later closer; an astral symbol or punctuation mark before, after or between two runs, two symbols, at
the paragraph's start and end, two URIs in one pair, and with two, three and five backslash-escaped astral symbols
before the opener so the mask correction accumulates), 18 of them red over a git archive of the reviewed head on both
renderers, each cutting the token at its end edge and linking a piece that is not the token, beside 8 controls identical
to the base grammar on both trees (an astral letter or a lone surrogate makes no token whole; the path arm splits at a
`*` or a non-ASCII character; U+3000 ends the URI token before the run); that a plain token keeps the edge rule with its
composed faces pinned as they render, the widening face's three rows among them since the 2026-09-21 review (forward,
`_see drafts/a_.md and old_ now`; backward, `_see x-_y.md now_`; spending a plain token's end-edge run, `_see final_.pdf
and /tmp/x_ now`; green at the reviewed head by construction, a recorded face, and red in a scratch copy hiding no run);
the escaped astral symbol's position; one scan of the paragraph per masked string per parse counted by execution (any
number of distinct nested strings between two delimiters one scan, the same paragraph parsed three times three, the
thrashing paragraph one scan and nine in all; red over the archive, whose list held the entry across parses and
rescanned the thrashing paragraph 571 times, and armed by a scratch copy with the memo's hit branch deleted, which reads
400); and the cost ratios against the base grammar under the bound of four on nine 20 KB shapes, the ninth the thrashing
shape, eight distinct nested `*` bodies between every two prose pairs (red over the archive at 28.9 and 31.8 times at
loads 17 to 21; 1.09 to 1.11 at the tree at loads 6 to 12, the eleven shipped shapes 0.67 to 1.65), its comment stating
that the bound was chosen, not derived, and why it is honest now. From the closing pass it also pins that an escaped
astral symbol inside a link, a reflink, a code span or a tag counts for nothing (seven rows keeping their emphasis as
the base grammar does and five whole-token rows staying literal and linked whole, red over round 2's head, with the
override's escape-rule passes counted at zero), the glued www opener `_www.x.co/a_/b.md now_`, its path analog
`_drafts/a_.md is here_` and the start-edge composed face `_see _posts/x.md and /tmp/_y/z.md now_` pinned as they render
with the walk's links, and two escape shapes in the ratio test.

Every test that stands in for a chat surface renders the chat's own instance since the 2026-09-21 review: nine stand-ins
re-aimed at chatMdHtml (the chat-links, chat-fragment, chat-modified-click, chat-schemeless, postpass, math-inks and
katex browser probes, and the pr-links and md-wiki node tests), each with an executed pin that a path's underscores stay
literal through it (red in a scratch copy where chatMarked loses pathAwareEmphasis, save md-wiki's, whose row holds no
linkable token, so its pin's reach is the import alone); chat-md.test.ts compares the user's instance against chatMdHtml
on its rows plus a path row and names the singleton's private copy for what it is; md-config-chat-styles-browser renders
its reply and notice roots on chatMdHtml and its viewer roots on the singleton through a second helper; the
browser-probe census in tools/file-review-viewer-recipe.test.mjs moved with them (4 modules spell the singleton probe,
all boxed; red over a git archive of the reviewed head); three prose sites stopped calling the singleton the chat's
(file-view-links.test.ts, md-literal-tags.test.ts, fileview-parity.test.ts); and the six source pins re-aimed by the
build (chat-md.test.ts, md-literal-tags.test.ts, md-config.test.ts, render-math.test.ts, render-sanitize.test.ts and
tools/file-review-plan-inlinetag.test.mjs) stand, the last two found by the build consolidation's whole-tree run; the
md-literal-tags, render-sanitize and tools pins also pin that chatMdHtml is marked's parse on chatMarked and nothing
else, and the sanitizer guard refuses an unsanitized return in either spelling of the parse. Every candidate's fixtures
render byte-identically on the singleton and on chatMdHtml at the reviewed head (3,155 distinct string literals from 15
test files, 0 differences, an armed control seeing the override's one difference), which is why every re-aim is green at
the head by construction and is proven by the mutation instead.

plans/file-review.md's decision 52 keeps its dated record (the chat's md() as marked.parse, as of 2026-09-18) and gains
a dated pointer sentence after it naming chatMdHtml in chat-md.ts as md()'s parse since 2026-09-19;
tools/file-review-plan-inlinetag.test.mjs pins the record and the pointer together beside its code pin (red over a git
archive of the reviewed head, whose plan lacks the pointer); plans/markdown-viewer.md's item 1 of the Slice 4 build note
carries the same pointer, unpinned there as its record was. In tests/test_file_preview_browser.py the lab gains
a-_b/c_/d.md, the driver waits for twelve links and prints the rendered ones when short, the driver parks the pointer in
the viewport's margin, out of every card's reach, and the two bare code-span cards take the checks the other eight take;
its docstring names the population note as a note kept outside the repo. md-literal-tags.ts and file-view.ts change in
comments only (review round 1): the sentence that named the chat's md() as a parse on the singleton now names the chat's
own instance; the viewer's code is byte-identical to main.

## Manager review round 1 (2026-09-21)

The manager's review of the whole change at its reviewed head (ten commits over main) ruled that it did not land: of 22
findings 18 were confirmed, seven medium and eleven low, and four were refuted and not refiled. Three things held it:
the whole rule had two holes, the asserted cost bound was violated by three to four times on a shape the tests could not
see, and the chat's rendering had moved without its stand-ins following. Every fix landed pinned at the head the defect
arrived at, and every class was fixed from a derived population rather than from the rows the review named. A, the whole
rule: the wholeness test had borrowed marked's punctuation rule, written to exclude the delimiters and read over one
code unit, so a `*` beside an interior run (the URI arm admits one) or an astral punctuation mark or symbol left the
token un-whole and cut from its edge; the test now states the emphasis spec's flanking class in the override's own words
and reads the neighbour by code point (md-config.ts FLANKING_RE and flankedInside), pinned by 23 URI-arm rows and 8
controls in md-emphasis-atomic.test.ts, 18 rows red over a git archive of the reviewed head. B, the cost: the
module-global eight-slot memo was evicted by eight distinct nested strings and the override then rescanned the paragraph
at every prose delimiter, quadratic where the base grammar is linear, 13.8 to 16.9 times the base on a 20 KB paragraph
the eleven pinned shapes could not reach; the algorithm is fixed, one memo per parse's lexer (linkableMemos), the
thrashing shape is the cost test's ninth row (red at 28.9 to 31.8 over the archive, 1.09 to 1.11 at the tree) and the
count pin follows the memo as landed; the bound of four was chosen, not derived, and the tests' comments say so and why
it holds now; the memo's value depends on the masked string alone, pinned by a throwaway instance with a punctuation
class of its own, red over the archive in either render order. C, the stand-ins: the renderers and every test site
standing in for a chat surface were derived (five roads and two static reads; 3,155 string literals from 15 test files
rendered through the singleton and the chat's instance, 0 differences at the head, so every re-aim is green by
construction and is armed by a mutation of chatMarked without the override): nine stand-ins re-aimed at chatMdHtml with
an executed aim pin each, chat-md.test.ts's equivalence test comparing the two shipped chat surfaces with a path row and
naming its local as the singleton's, md-config-chat-styles-browser split into a chat helper and a viewer helper, three
prose sites and the mdExtensions docstring corrected, the browser-probe census moved, none retired; md-wiki.test.ts's
re-aimed row holds no linkable token, so its pin reaches the import alone, recorded. D, the class: the whole-token
rule's cost is recorded above with both faces at the rule level (106 rows; the bare-name arm the pure-cost case; the
widening face pinned by three FACES rows, armed by a mutation), the chat grammar's own constructs (39 rows) entail
nothing new and take a clause beside the member rule, the `^[..]` row is dropped as identical on both trees, and the
list of differing rows is called the sample it is. E, the proxy: the recording proxy records the stand-in's lexer reads
too, exactly inlineTokens, and DRY_LEXER's comment says what the pin promises (what the installed marked read, not what
a later version would) and that marked's version is held by the lockfile, not enforced by a build check; the instanceof
branch's comment names the callers that reach it. F, the rule's pin: THE RULE is pinned by execution with a stub in
path-links.ts's place and over the bare gate's live values (a bare-name grammar of the override's own under a sixth
spelling, blind to the old blacklist and to every table, reds both), and the instance boundary is a census over the tree
(eleven importers of marked; a twelfth goes red by name). G: decision 52's dated record keeps its verbatim pin and gains
a dated pointer pinned beside it; the queued twin's item above says both halves; and the two code comments and the
browser lab's docstring that cited the population note by bare name say it is kept outside the repo, the commit arm
declined because the rows are executed in-repo and the note quotes a recorded path. The round's three derivations are
notes kept outside the repo beside the population note: the renderers and stand-ins with the importer census (the
population C and F were fixed from), the cost's worst case and four candidate memo shapes by measurement (the algorithm
arm chosen over moving the bound, which no constant could honestly do, and over a length-aware eviction whose body memo
degenerated to thousands of scans), and the class with both faces, the constructs and the wholeness class by code point
with its 40 probe rows (D and A). The sections above were re-read against the round: How the override decides and
Boundaries against main carry the round's corrections; Upstream placement and Recorded, not fixed stand as written.

## Upstream placement

The road is shared with the project, not fork-only (checked against upstream main 944537e9f, 2026-09-19): the chat's
path walk (path-links.ts linkifyPathTokens, render.ts linkifyFileUris), the kernel's pathLinks map (kernel.py
_path_tokens and _path_links) and marked 12.0.2 with gfm on and breaks off all exist upstream, so the defect does too.
What is fork-only is md-config.ts, the shared-grammar module the override lives in, and the boundary between the chat's
two instances and the singleton, so an offer needs a home of its own there: upstream's chat-md.ts holds chatMdExtensions
and userMarked, and render.ts's singleton renders the chat and the viewer alike. This change does not settle that
placement.

## Recorded, not fixed (owners to be placed)

Three items met in the build and the review, each pre-existing, none changed by this fix, each named with its file so it
can be routed.

(a) ui/webview/file-view-links.ts: the viewer's own link walk has the same gap over a note's prose. A path whose
underscores pair as emphasis is never linked in the viewer: `foo/__pycache__/bar.pyc` renders
`foo/<strong>pycache</strong>/bar.pyc`, `/a-_b/c_/d.md` renders `/a-<em>b/c</em>/d.md` and `/pkg/__init__.py` renders
`/pkg/<strong>init</strong>.py`, with no .file-uri-link on any of them; the walk reads three text nodes and path-links.ts
spanHolding returns null. Reproduced in headless Chromium on the Files pane bundle at the head and on main, with
byte-equal HTML, text nodes and links on all eight probe rows; the controls (no pair, a code span, a one-sided run, a
wholly wrapped path, intraword underscores) link on both. By the time linkifyFileText runs, the singleton has rendered
the pair as `<em>` or `<strong>` and the underscores are gone from the DOM, so loosening spanHolding would stamp a link
on the wrong path. The singleton (file-view.ts viewerHtml, anchor-map.ts, render.ts previewMdClean) keeps GitHub's
rendering by design, under the plan's standing rule (plans/markdown-viewer.md) that changes to the viewer cause the
file-comments feature no trouble; the files bundle carries no pathAwareEmphasis on either tree. Two fix shapes for the
owner: the override on the singleton (the anchor map and the hover preview follow; the feed's notice cards on their own
bare instance, feed.ts noticeMarked, do not; the GitHub-rendering aim goes) or a private instance shared by viewerHtml
and anchor-map.ts (the anchor map must follow so the offsets stay paired). The pins to lift by shape are in
md-emphasis-paths.test.ts's instance boundary test (the singleton's rendering and the shared list, or the file-view.ts
line). The star gate in file-view-links.ts governs literal asterisks in a code view, not the rendered view; wholly
wrapped paths do link in the viewer, and the loss is confined to a delimiter inside the token.

(b) ui/webview/path-links.ts against kernel/kernel.py: the client's ASCII word class splits an accented path the kernel
keys whole. CLICKABLE_PATH_RE's `\w` is ASCII in JS with or without the u flag, and isWordCh is its hand-written twin;
the kernel's _PATH_TOKEN_RE is a str pattern without re.ASCII, so Python's `\w` matches U+00E9, and _path_tokens keys
the whole path. Measured: a reply naming `/a-_b/cé_/d.md`, an existing file, ships a pathLinks map keyed on the whole
path; the chat now renders it literal, so the DOM text equals the key, but the walk's scanner reads `/a-_b/c` and
`_/d.md`, both passing the gates: with the map nothing links, with no map two links appear, each to a path that does not
exist. `/tmp/naïve_x/y.txt`, `docs/ré_sumé/notes.md` and `/tmp/café/menu.md` split the same way with no emphasis
involved; the ASCII control `/a-_b/c_/d.md` reads whole. Inside a prose pair, `_see /a-_b/cé_/d.md now_` renders
`<em>see /a-_b/cé</em>/d.md now_` with no link (the row set: that row, `_see /a-_é/c_/d.md now_` and
`_see /_x/café_/menu.md now_`), because the second piece is a plain token whose start-edge run keeps the edge rule; on
main the base grammar cut the path into em and the walk linked `/a-` and `/d.md`, so the link loss is the same on both
trees and the fix changed only the rendering. path-links.ts differs from main on this branch only by the trailingPunct
export; kernel.py and tests/fixtures/path_token_parity.json are unchanged. The fix is a contract change on both
tokenisers, or a client-side key normalisation, and its first step is a non-ASCII row in
tests/fixtures/path_token_parity.json (12 cases and 0 non-ASCII characters today), which pins whichever contract is
picked; the scanner is shared with the viewer's walk through file-view-links.ts, file-view.ts, render.ts, url-links.ts
and waiting.ts. The rows are pinned as they render in md-emphasis-atomic.test.ts (the plain token test's FACES).

(c) ui/webview/path-links.ts and kernel/kernel.py _path_tokens: two parity follow-ups from the derivation, both from the
kernel tokenising the raw markdown while the client tokenises the rendered DOM. C41, a backslash-escaped path:
`see /a-\_b/c\_/d.md today` renders `see /a-_b/c_/d.md today` on both trees (the escapes are literal), the DOM holds one
token, `/a-_b/c_/d.md`, and the kernel keys three, `/a-`, `_b/c` and `_/d.md`, so the lookup misses. The override cannot
close this: it reads marked's masked string, where an escape is `++`, and the kernel splits at the backslash the same
way (`see /a\-_b/c.md and x_ ok` renders `see /a-<em>b/c.md and x</em> ok` and `a-_b/c_/d\.md` renders
`a-<em>b/c</em>/d.md` on both, and a relative path escaped in its last segment loses the extension its gate needs). C42
and C43, a wrapped path: `_docs/notes.md_` renders `<em>docs/notes.md</em>`, the DOM holds `docs/notes.md` and the
kernel's key is `_docs/notes.md_`; `~~/old/notes.md~~` renders `<del>/old/notes.md</del>`, the DOM holds `/old/notes.md`
and the kernel's key is `~~/old/notes.md`; with a map present neither links. The same face on a plain token's edge:
`_see /tmp/x_` gives the DOM `/tmp/x` against the kernel's `/tmp/x_`, and `see _docs/x_/notes.md_ now` renders
`see <em>docs/x</em>/notes.md_ now` on every tree (the wrapped string is one scanner token that fails the file gate on
its trailing `_`). The kernel keys were re-verified by execution over the kernel's own tokeniser. The fix belongs to the
kernel's tokeniser or a client-side key normalisation. md-emphasis-paths.test.ts carries a comment block over rows C41 to
C43 saying its `links` map holds the DOM token the walk sees and the kernel's differing key would link nothing;
md-emphasis-override.test.ts's second test pins C42's row as recorded, not changed.
