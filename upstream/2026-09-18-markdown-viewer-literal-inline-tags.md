---
title: An inline start tag with no end tag in its block renders as literal text in the file viewer, where it used to nest or hide the rest of the note
status: candidate
where: ui/webview/md-literal-tags.ts (new: literalizeUnclosedTags, VOID_ELEMENTS, IMG_ALIAS, isSelfClosingTag, escapeInlineText), ui/webview/file-view.ts mdBlock (marked.parse's three steps called apart, the rule between the lexer and the walk), docs/guide.md (the paragraph on a file's own HTML); tests: ui/webview/md-literal-tags.test.ts, ui/webview/md-literal-tags-tag-syntax.test.ts, the mdBlock pins in ui/webview/file-view.test.ts, file-view-links.test.ts, render-sanitize.test.ts and md-config-merged-paragraph.test.ts, tools/guide-own-html-block-tag.test.mjs; the anchor-map half (anchor-map.ts placeTokens and its suites) is fork-only
added: 2026-09-18
pr:
tier: fix
offered:
closed:
---
The viewer half is separable from the anchor map, which upstream lacks. marked lexes a tag written mid-line (a placeholder such as `(<table>__widths.csv)`) as an inline html token and passes it through; in DOMPurify's quirks-mode document a `<table>` start tag closes no open `<p>`, so every later block nests inside the paragraph, and an inline `<title>`, `<script>`, `<style>` or `<textarea>` start tag takes the rest of the note as its text, which the sanitizer drops. The rule converts such a token to a text token on the parse's own tree, nothing registered on the marked singleton, so the chat's md() renders as before; matching is by name, innermost first, with void elements, the image alias and the self-closing syntax left HTML. Decision 52 of plans/file-review.md. The user decides whether this is offered alone or folded into the file-comments umbrella (2026-09-07-file-comments-tracked-changes.md), which covers the map.
