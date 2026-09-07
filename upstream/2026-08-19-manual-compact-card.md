---
title: A live manual `/compact` produces no "Context compacted" card in the chat — the CLI writes the boundary+summary as a DETACHED side branch (parentUuid null + logicalParentUuid:<pre-compact leaf>; the conversation chains through the /compact command wrappers instead), so the leaf→root walk never visits the pair and the compact atom is never emitted; auto-compactions, which chain THROUGH their boundary, keep theirs
status: merged
where: fork branch `compactcard`: `kernel/event_model.py` `FileAdapter._adopt_detached_compactions`
added: 2026-08-19
pr:
tier:
offered: their PR #539
closed: 2026-08-22
---
MERGED as-is 2026-08-22 (head is an ancestor of their main, verified in the fold). Branch retired. OFFERED 2026-08-20 (branch `compact-card`, `fcc89f58` off tip `f3ec1297`): the no-PLACEMENTS_V-bump judgment call is flagged to the maintainer in the body with an offer to add one — it shipped as offered, no bump; review clean, scaffold CI green (since-closed fork #92). Upstream ships the same walk verbatim, so their manual compacts lose the card too. Fix is a self-contained event-model adoption repair: splice the detached boundary(+summary) back in AFTER its own /compact invocation episode's stdout record (episode found via the summary record's promptId — the CLI stamps it with the invoking /compact's — with file-order fallback), gated on the EPISODE being on the active path, never on trigger or the bare anchor — attached boundaries (auto, and the resume re-splices manual ones arrive as) no-op, a rewound-away /compact stays hidden with its history, and an adopted boundary never arms the post-compaction replay dedup (a live manual compact replays no tail; armed, it silently ate the user's next typed prompt whenever its text repeated an earlier message). Shape verified against the live corpus (10/13 manual boundaries detached — the other 3 are resume re-splices that arrive attached and no-op — and 13/13 manual summaries carry the episode promptId); pinned red-first (golden scenario + replay-dedup class + unit class + warm/cold incremental-cache equivalence + placements canary). Placements: unit sets identical pre/post on the golden scenario and 11/12 boundary-bearing corpus transcripts; the residue is one continuation-work unit re-attributed from the /compact command segment to the boundary turn when queued work continued straight through the compact (the attached-compact shape).

Status detail (migrated from the table): ✅ **merged** — their PR #539, merged as-is 2026-08-22 (merge `9fd6dcf7`); came home in the 2026-08-22 tip fold (`upfold0823`)
