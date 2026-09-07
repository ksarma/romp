---
title: `_note_served_model` logs once per process when a judge envelope carries no `modelUsage`
status: offered
where: not built; from the maintainer's review comment on their PR #948 (2026-09-06): `kernel/judge.py` `_note_served_model` (reads `modelUsage` from the envelope)
added: 2026-09-07
pr:
tier: fix
offered: their PR #967
closed:
---
An envelope with no `modelUsage` field is silent today, so a stale alias table would stay trusted with nothing logged; a once-per-process stderr line satisfies the loud-failure rule. Natural pair with the `_ALIAS_SERVED.clear()` setUp part of the tests-only follow-ups bundle (`batch12-review-tests-only-followups`): both touch #948's code.

APPROVED 2026-09-07: the fork owner said offer it (batch 13, tier fix). #948's head `e6edcab8` is not on fork main; build off upstream/main. Fork side, open PR #275 touches `kernel/judge.py`.

OFFERED 2026-09-07: offered upstream as their PR #967 (2026-09-07, label fix, head 74db19a3); one PR for six entries: `stale-setting-toast-liveness`, `kernel-small-fixes-taskupdate-tick-pn`, `find-orphan-clis-own-pid`, `note-served-model-no-modelusage`, `github-link-ls-remote-askpass`, `manager-scoped-tmux-etimedout-line`.
