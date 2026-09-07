---
title: Perf B2: the chat fold seals plain Bash turns (a Bash tool event is postal-relevant only when the shared matcher recognises a `romp mail send` or a mail read, and relevance reads only the input), and `enrich_out` joins outgoing postal cards through a body-keyed map built once per postal index version instead of scanning the whole index per card
status: candidate
where: fork PR #214 (`perf-b2`, merged 2026-09-06): `kernel/kernel.py` (`_chat_postal_relevant`, `_hydrate_postal`, the body map on the postal index memo, `enrich_out`); tests `tests/test_chat_fold.py` (`PostalCards`, `PostalRelevance`)
added: 2026-09-07
pr: 214
tier: fix
offered:
closed:
---
Upstream's `build_session` has the same shape: every Bash tool event counts as potentially postal, so every plain Bash turn stays unsealed and is re-hydrated on each rebuild, and the outgoing-card enrichment scans the whole postal index once per card. `build_session` was 22 to 24% of the kernel's interpreter time in the 2026-09-06 profile and over half of that was `_hydrate_postal`. A tool result landing later cannot change relevance, because the predicate reads only the input. The invariant pinned by test: for any event the predicate rejects, `_hydrate_postal` returns the very same object. Tie-breaking in the join is unchanged (closest in time wins); non-string bodies, which the far-host relay can write, stay in the index and are absent from the map, so they no longer raise inside the index build. Measured on five transcripts through the offline bench: warm chat builds down 15 to 52%, cold builds unchanged (they never consult the fold).

Port note: the predicate names the fork's shared matcher `_cli_send_match`, which `upstream/main` lacks (checked 2026-09-07); re-derive the predicate over upstream's `romp mail send` recogniser. A pre-existing bug found on the way and left for its own change, seen in the fork and not checked upstream: outgoing cards never render for real `romp mail send` Bash rows, because the stored input is JSON-wrapped and the unquoting rejects the captured group.
