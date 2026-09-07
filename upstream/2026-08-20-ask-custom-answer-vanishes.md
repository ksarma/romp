---
title: AskUserQuestion "write your own answer" replies unreliably vanish from the chat's answered box — the kernel joins answers by regex-scraping the tool_result's flat output string while the SAME user record carries the structured `toolUseResult = {questions, answers}` map, and the event model drops top-level `toolUseResult` from atoms entirely, so the attach loop's `tur` is always None (which also leaves Edit's structuredPatch `diffRows` dead through the parse path); any double-quote inside a question's text breaks the scrape and the typed answer disappears (13 of 95 real answers dropped, 1 garbled, all quote-correlated)
status: merged
where: fork branch `askanswer`: `kernel/event_model.py` carries dict `toolUseResult` on tool_result atoms; `kernel/kernel.py` `_ask_fill_answers` fills `chosen` by exact question-text key (string → one value, LIST → the multiSelect picks), regex kept only for old records without the dict; `multiSelect` copied onto askAnswer blocks
added: 2026-08-20
pr:
tier:
offered: their PR #576
closed: 2026-08-23
---
MERGED as-is (head is an ancestor of their main, verified same day). Branch retired. OFFERED 2026-08-23 (branch `ask-answers`, `830bba16` off tip `147678b1`, two commits per the coupled halves): structured answers join + toolUseResult carried onto atoms; only 10e3b55d’s test hunks travelled; review clean, scaffold CI green (since-closed fork #105). Upstream ships the whole chain verbatim (their atom builder, their `_ask_fill_chosen` + the always-None `tur`, and the missing `multiSelect` on blocks — their ", " split is dead code, so multiSelect picks render as ONE joined quoted "Other" row instead of highlighted options). Render side needs no change (chosen is already per-value matched). Pure bug fix, no fork-specific content; pinned red-first in tests/test_kernel_askanswer.py (10 new tests red on unfixed code, incl. the authoritative-skips-regex overwrite case and the old-record fallback).

Status detail (migrated from the table): ✅ **merged** — their PR #576, merged as-is 2026-08-23 (merge `65ab2c7f`)
