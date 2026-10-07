---
title: docs/stylesheets/extra.css: the Mermaid-legibility comment closed twice (a ` */` at the end of its second paragraph and another after the five lines of commentary the 2026-07-24 selector fix added between that close and the rule), so a CSS parser read those five lines and the `:root, :root > *` after them as one invalid prelude and dropped the rule with both --md-mermaid-label-* custom properties, the fix for near-white node labels on pale boxes on the dark scheme; the stray close is gone and tests/test_docs_stylesheet.py pins comment balance over the whole sheet (a `*/` outside a comment or a `/*` open at end of file, each naming its line) and the rule as parsed with both declarations, by execution on the smallest inputs and on the real sheet with the defect replanted on every line of the comment
status: candidate
where: docs/stylesheets/extra.css, tests/test_docs_stylesheet.py
added: 2026-09-22
pr:
tier: docs
offered:
closed:
---
Upstream ships the same sheet with the same two closes, so its docs site drops the same rule; the comment fix and the pin apply as they are. Found by the reviewer of fork PR #862 (its CSS rule reader, run over every sheet in the tree); the reader, when it lands, is where this narrower check folds in. docs tier: a stylesheet comment and a test.
