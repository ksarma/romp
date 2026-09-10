---
title: KaTeX bounds in the math grammar: a per-formula size cap (maxSize 50 em), a per-formula macro-expansion budget derived from the longest macro body (maxExpand), and two TeX length bounds (20,000 characters a formula, 100,000 a message), with the fill's error colour as a theme token
status: candidate
where: ui/webview/math.ts (MATH_TEX_MAX_CHARS, MATH_TEX_BUDGET_CHARS, MATH_MAX_SIZE_EM, MATH_EXPANSION_BUDGET_CHARS, maxExpandFor, KATEX_OPTIONS with errorColor MATH_ERROR_COLOR, the tokenizer's length checks); tests ui/webview/render-math.test.ts (the bounds and the option pins), md-config-math-error-colour.test.ts and its browser leg, md-sanitize-katex-browser.test.ts (the capped layout identical to katex.render's own output for ordinary formulas); docs/reference.md's math paragraph
added: 2026-09-10
pr:
tier: fix
offered:
closed:
---
KaTeX renders with maxSize Infinity and maxExpand 1000 by default, so a reply's formula can lay a 78,650 px square (a 5000 em rule) or expand a 1,000-character macro body 200 times into 200,000 characters of formula and 20 s of render on the shared main thread; the fork's chat grammar (Slice 3 of plans/markdown-viewer.md, review rounds 3 and 4) caps each size a formula asks for at 50 em (about the chat column, so ordinary layout is byte-identical), bounds one formula's TeX at 20,000 characters and one message's at 100,000, and computes maxExpand per formula as an expansion budget divided by the longest macro body the formula defines, never above KaTeX's default; the error ink is a theme token instead of KaTeX's hard-coded red. The project's markdown sanitizer offer (romp-on/romp#1196, folded as fork PR #598) took trust: false alone, so these bounds are fork-only; promised as an offer to the fold's owner during the slice 4b rulings (2026-09-10). Offer as one fix PR carrying math.ts's constants and maxExpandFor with their render-math pins; the error colour token can ride along or wait for the theme tokens offer.
