---
title: Three small kernel fixes from the batch-12 merge comments: the TaskUpdate `is_error` skip, one try/except around the WS-thread ticks, the bell's `PN` map from `_PANE_ORDER`
status: approved
where: not built; from the maintainer's merge comments on their PRs #942, #943 and #957 (2026-09-06): `kernel/kernel.py` `_fold_tasks`' TaskUpdate branch and `kernel/event_model.py` `declared_plan` (both folds); the `setAutoNudge` / `setCompactSuggest` arms of `_dispatch_ws`; the shell's bell JS pane-label map `PN`
added: 2026-09-07
pr:
tier: fix
offered:
closed:
---
Three parts, one fix PR or one each: (1) the #942 TaskCreate guard keys its skip on the paired tool_result's `is_error`, but a rejected TaskUpdate is still applied in both folds, so apply the same rejection-keyed skip to keep the two folds identical, with a test; (2) the reader loop re-raises OSError as a socket failure, so an OSError out of `_auto_nudge_tick`'s pass head on the WS thread closes the dashboard connection with no log line (the `setCompactSuggest` arm has been unwrapped since #846) — one shared try/except around both arms, as the pusher already has; (3) the bell's pane-label map is a second hand-written list, so splice `PN` from `_PANE_ORDER` as the rail and tabs do (the fork's copy has already drifted to six entries).

APPROVED 2026-09-07: the fork owner said offer it (batch 13, tier fix). Build off upstream/main (the #942 head `9b974149`, #943 head `c334e4f0` and #957 head `51eaec7a` are not on fork main). Fork side, open PRs #271, #258, #272 and #275 touch `kernel/kernel.py`.
