---
title: PR links: the boundary before a reference is judged over the rendered text, not per text node
status: merged
where: upstream branch pr-links-carry-offer, re-derived from fork PR #346 (commits 37007fa3, 02321716, 4450974a): `ui/webview/pr-links.ts` (prRefSegments's optional `before` parameter, the BOUNDARY constant, visit()'s carry across inline elements, BLOCK_TAGS reset); tests `ui/webview/pr-links.test.ts` (three new cases: the rendered-text boundary, element glue, marked shapes and block edges)
added: 2026-09-09
pr:
tier: fix
offered: their PR #1212
closed: 2026-09-09
---
Audit row 12, a generalisation: a #12 written right after inline code, emphasis or a link (docs/a.md in backticks then #12) linked to a PR because the word-boundary rule was judged per text node. The boundary is now judged over the rendered text; what follows a reference stays per node (outside this change).
