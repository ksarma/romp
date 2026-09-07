---
title: Resume guard for the spend watermarks: a connect seeds the cost and token watermarks from the resumed transcript's last `cost-state` record (the CLI's restore-on-resume path writes `totalCostUSD` + `modelUsage`, filed last-wins) so a CLI that restores its counters does not fold the session's history as one turn (re-seeded when init corrects the cwd, from the sid the CLI loaded when that same init also landed a new fsid); the first result after a connect that folds more than 200 USD is recorded as is and traced once as an info line
status: approved
where: fork main `a76288e9` (2026-09-05): `kernel/sdk_backend.py` (`SANE_TURN_USD`, `last_cost_state`, `SdkSession._seed_spend_watermarks`, the first-result check in the settle branch); tests in `tests/test_sdk_backend.py` (`SpendRecord`, the resume-guard tests)
added: 2026-09-06
pr:
tier: fix
offered:
closed:
---
Fork `a76288e9` (2026-09-05). On 2.1.261 the CLI's cost-state writer fires in a print-mode (SDK) process only at the second and later /clear, into the episode that /clear abandons. The episode romp resumes (the reg's lastSid) never carries a record, and a print-mode resume restores nothing, so today the seed reads zero and the CLI starts at zero. The guard is for the day a print-mode CLI restores the record. The first-result check above 200 USD is an info line, not a problem. The pre-flip re-seed (2026-09-06) matters only for a CLI that restores history in print mode. Upstream runs the same settle code.

Status detail (migrated from the table): candidate

APPROVED 2026-09-07: the fork owner said offer it (batch 13, tier fix — offer on their #956's head or after it merges (#956 leaves the watermark logic unchanged); low urgency on its own, since a 2.1.261 print-mode resume restores nothing).
