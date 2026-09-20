---
title: The chat renderer keeps a path's underscores literal: no emphasis delimiter opens or closes inside a token the path walk would link
status: candidate
where: ui/webview/md-config.ts (pathAwareEmphasis, an emStrong tokenizer override exported beside mdExtensions and not in that list; its helpers linkableRuns, tokenAt, proseRun and shiftedEscapes, the constants DRY_LEXER, HIDDEN and MEMO_SLOTS, the type LinkableRuns and the linkableMemo list; the boundary list in its comments); ui/webview/chat-md.ts (chatMarked beside userMarked, both taking the override; chatMdHtml); ui/webview/render.ts (md() parses through chatMdHtml; the chat-md import and the grammar comment above the singleton); ui/webview/path-links.ts (trailingPunct exported); ui/webview/md-emphasis-paths.test.ts (new; nine tests: the chat renders every member row literal, every other row is byte-identical to the base grammar, the adversarial rows change only where the note says, the user's own words take the same grammar, the chat's walk links every wanted token whole, the base grammar cuts every member row's token, a footnote reference inside a refused pair is numbered once, a file URI and the block contexts are protected too, the instance boundary); ui/webview/md-emphasis-override.test.ts (new in review round 1; five tests: a pair whose body holds a path with an unbalanced interior run keeps its emphasis, the shapes around it stand, the dry-run stand-in is rules and lexer, no extension the chat's instances take overrides emStrong besides pathAwareEmphasis, the override costs at most a few times the base grammar); ui/webview/md-emphasis-atomic.test.ts (new in review round 2; six tests: a linkable token with a run beside punctuation inside it is one word whole, a plain token keeps the edge rule and its FACES, a backslash before an astral symbol masks three UTF-16 units as two, an escaped astral symbol inside a link, a reflink, a code span or a tag counts for nothing, one scan of the paragraph per masked string, the override costs at most a few times the base grammar on a 20 KB paragraph); six re-aimed source pins: ui/webview/chat-md.test.ts (the singleton stays breaks:false), ui/webview/md-literal-tags.test.ts (source: one rule, two callers), ui/webview/md-config.test.ts (source: who applies the one configuration), ui/webview/render-math.test.ts (render.ts wires the math extensions into marked), ui/webview/render-sanitize.test.ts (md() sanitizes marked output with DOMPurify, and its CHAT read of chat-md.ts), tools/file-review-plan-inlinetag.test.mjs (md-literal-tags.ts exports the function and the void list); tests/test_file_preview_browser.py (ServedFilePreview._boot's lab, the hover test test_a_hover_previews_the_file_or_its_section_after_the_dwell_and_a_refused_path_is_text_with_no_request, the DRIVER string's link wait and PARK, the module docstring); comments only: ui/webview/md-literal-tags.ts (the one-rule-one-code-path comment) and ui/webview/file-view.ts (the viewerHtml docstring). Upstream-facing: path-links.ts, render.ts and chat-md.ts (upstream's holds chatMdExtensions and userMarked) exist upstream, as do kernel/kernel.py's _path_tokens and _path_links; fork-only: md-config.ts, the module the override lives in
added: 2026-09-19
pr: 869
tier: fix
offered:
closed:
---
Reproduction credit: romp-upstream's browser census (browser-flake/census-2026-09-19.md, Entry 5, a note kept outside the repo) read one CI failure of tests/test_file_preview_browser.py to its mechanism: the lab's random temp name began with an underscore and a later segment ended with one, CommonMark's flanking rules made the pair an emphasis, the chat rendered the outside path's middle as em, and the link walk never saw the token whole (about 3 in 37 squared per run; the test was a bystander). The derivation is md-emphasis-population.md (a note kept outside the repo; 55 rows and 20 adversarial rows, each measured against marked 12.0.2, the CommonMark reference implementation, the chat's walk and the kernel's tokeniser): marked is spec-correct on every row, so the class is the chat's road, which renders a reply as prose markdown over text the kernel has already tokenised as a path, and the fix is an emStrong override on the chat's marked instances that hides a `_` run lying strictly inside a token the walk's scanner and gates would link (the bare-filename gate included, so a bare name in prose is protected and still not linked) from the built-in's closer scan, and refuses an opener, or a spent closer run, lying strictly inside such a token, so a prose pair spanning a path keeps its emphasis around the literal path; a token holding a `_` run beside punctuation inside it is one word whole, its edge runs included, while a plain token's edge run pairs as the spec says (review round 2). Measured: exactly the 20 member rows change, every one to the literal token, none of the other 35; of the adversarial rows only A08 (emphasis glued to a path with no space between, the accepted loss), A12, A14 and A20. Boundaries: a glob (src/*.py) is outside the linkifier's grammar and renders as before; the singleton (the viewer, the hover preview, the anchor map) keeps GitHub's rendering, as do the feed's notice cards on a bare instance of their own (feed.ts noticeMarked, which links no paths), and whether the viewer's own walk (file-view-links.ts) should follow is a separate decision. Two parity follow-ups stand outside this class, both from the kernel tokenising the raw markdown while the client tokenises the rendered DOM: a path wrapped in markup gives the kernel a key the DOM never shows, and a hand-escaped path is one token to the DOM and three to the kernel.

## How the override decides

pathAwareEmphasis (md-config.ts) is an emStrong tokenizer override. The built-in decides the pair on a dry stand-in
whose lexer lexes nothing, over a masked string in which every `_` run lying strictly inside a linkable token is hidden
from its closer scan, so a prose pair spanning a path keeps its emphasis around the literal path. A token holding a `_`
run beside punctuation inside it is one word whole, its edge runs hidden and refused with the rest (review round 2: an
edge run left visible paired across the hidden middle with a partner outside the token), while a plain token's edge run
pairs as the spec says. An opener, or a spent closer run, that is a path's is refused, the opener before any scan.
Linkable is the walk's own scanner, trailing-punctuation trim and shape gates, all imported from path-links.ts and never
restated, and the flanking test is marked's own punctuation rule. A star run falls through to the built-in. The
paragraph is scanned once per masked string and remembered in an eight-slot most-recently-used list (MEMO_SLOTS), so the
nested lexes of a link's label or a star or tilde pair's body evict the paragraph's entry only once eight or more
distinct such strings holding a `_` run are lexed between two of the paragraph's delimiters, past which the paragraph is
rescanned once per such gap (the review's closing pass, counted by execution: seven distinct labels between two prose
delimiters one scan, eight two, eight identical ones one). A run's position counts the escaped astral symbols the mask
shortens, read at the masked string's `++` positions off the tail; an escape inside a link, a reflink, a code span or a
tag counts for nothing, since marked masks those to letters before its escape rule runs (the closing pass; round 2
counted every escape in the tail). In render.ts only md() changes road: the singleton, the viewer, the hover preview and
the anchor map are untouched.

## Boundaries against main

Each row was measured on main's chat road (the singleton after applyMdConfig, and its userMdHtml, which agree on every
row) and at the head in the review's closing pass. The rows that render differently from main by this rule:

- The accepted loss A08, `_foo_-bar/baz.md`: main `<em>foo</em>-bar/baz.md`, the head literal and linked whole.
- Its `~~` glue, `__note/a.md__~~x.py~~`: main `<strong>note/a.md</strong><del>x.py</del>`, the head
  `__note/a.md__<del>x.py</del>`, linked on neither.
- A plain token's end-edge closer longer than the pair spends, `_see /tmp/x__`: main `<em>see /tmp/x</em>_`, the head
  literal with `/tmp/x__` linked under the kernel's key.
- The URI arm glued to a mask or to punctuation: `file:///x/y.md[link](u)_bar_` (main `<em>bar</em>` after the link,
  the head `_bar_`) and `see file:///x/y.md._draft_ now` (main `file:///x/y.md.<em>draft</em>`, the head literal).
- The www autolink, `_see www.x.co/a_/b.md now_`: main cut the URL at its underscore,
  `<em>see <a>www.x.co/a</a></em>/b.md now_`; the head renders one emphasis around the whole autolinked URL.
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
- The queued twin's line (render.ts renderQueued, outside the change's three render.ts hunks).
- The wrapped path `see _docs/x_/notes.md_ now`: `see <em>docs/x</em>/notes.md_ now` on both.
- The plain token's edge rule rows: `_see /tmp/x_` (`<em>see /tmp/x</em>`), `_x/y.md and more_`
  (`<em>x/y.md and more</em>`) and `_see _posts/x.md now_` (`_see <em>posts/x.md now</em>`), each on both.

The round 2 commit's body called the label item, the URI arm's rendering and the glossary result identical on main,
which they are not: this list and the code's boundary list (the boundaries comment in md-config.ts) are the record.

## Tests

md-emphasis-paths.test.ts (new) runs the 55 rows and the 20 adversarial rows through both chat renderers, the walk over
the rendered DOM with the kernel's map, the base grammar's cut, the footnote count, the block contexts, a file URI, the
instance boundary and the feed's bare instance. md-emphasis-override.test.ts (new in review round 1) pins that a pair
spanning a path with an unbalanced interior run keeps its emphasis on both chat renderers, the stand-in's contract by a
recording proxy, the emStrong chain, and the cost ratios against the base grammar. md-emphasis-atomic.test.ts (new in
review round 2) pins that a token with a run beside punctuation inside it is one word whole on both chat renderers and
the walk links it under the kernel's key, that a plain token keeps the edge rule with its two composed faces pinned as
they render, the escaped astral symbol's position, one scan per masked string counted by execution, and the cost ratios
against the base grammar; from the closing pass it also pins that an escaped astral symbol inside a link, a reflink, a
code span or a tag counts for nothing (seven rows keeping their emphasis as the base grammar does and five whole-token
rows staying literal and linked whole, red over round 2's head, with the override's escape-rule passes counted at zero),
the memo's bound counted by execution (seven distinct labels or star bodies between two prose pairs one scan and eight or
nine two, twelve identical labels one), the glued www opener `_www.x.co/a_/b.md now_`, its path analog
`_drafts/a_.md is here_` and the start-edge composed face `_see _posts/x.md and /tmp/_y/z.md now_` pinned as they render
with the walk's links, and two escape shapes added to the ratio test. Six source pins were re-aimed at the changed lines
(chat-md.test.ts, md-literal-tags.test.ts, md-config.test.ts, render-math.test.ts, render-sanitize.test.ts and
tools/file-review-plan-inlinetag.test.mjs), the last two by the build's consolidation, whose whole-tree run found them;
the md-literal-tags, render-sanitize and tools pins also pin that chatMdHtml is marked's parse on chatMarked and nothing
else, and the sanitizer guard refuses an unsanitized return in either spelling of the parse. In
tests/test_file_preview_browser.py the lab gains a-_b/c_/d.md, the driver waits for twelve links and prints the rendered
ones when short, the driver parks the pointer in the viewport's margin, out of every card's reach, and the two bare
code-span cards take the checks the other eight take. md-literal-tags.ts and file-view.ts change in comments only
(review round 1): the sentence that named the chat's md() as a parse on the singleton now names the chat's own instance;
the viewer's code is byte-identical to main.

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
