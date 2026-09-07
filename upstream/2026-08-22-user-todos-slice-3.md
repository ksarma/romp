---
title: User todos slice 3 — memory across context loss: a SessionStart hook (resume + compact sources) hands a resumed/compacted session its open todos as passive additionalContext, rendered kernel-side over a read-only `POST /usertodo/context` so the voice test scans exactly what a session receives
status: approved
where: fork branch `usertodos` (commit `57b085bc`; `hooks/romp-usertodo-context.sh`)
added: 2026-08-22
pr:
tier: major-feature
offered:
closed:
---
(the user 2026-09-06: one of two example major features to offer in future) Upstream ships the same SessionStart hook family (`hooks/romp-postal-context.sh`, install.sh registration) and the same SDK/tmux split the hook straddles. Depends on slice 1.

Status detail (migrated from the table): candidate — **major-feature (tier 3)**, discuss with the maintainer first

APPROVED 2026-09-07 as an RFC: the fork owner approved offering the user-todos slices upstream as an RFC rather than a straight code PR — with docs and demo captures (headless captures over synthetic notes-api content only). Tier 3 stays: discuss with the maintainer first; the three slices travel as one conversation.
