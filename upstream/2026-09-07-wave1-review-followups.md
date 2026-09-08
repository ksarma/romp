---
title: Wave-1 review follow-ups: pre-push hook new-ref exclusion and merge second-parent scan; manager placementFromCgroup login-session read; gear staleWord Default pick; #964/#965 wording nits
status: merged
where: fork branch wave1-review-followups-offer, head 7f238149; from the maintainer's comments on #968, #967, #964, #965
added: 2026-09-07
pr:
tier: fix
offered: their PR #971
closed: 2026-09-07
---
Four parts from the maintainer's merge comments on the wave-1 PRs, built as one fix PR: the pre-push hook's new-ref exclusion and merge second-parent scan (#968, entry `pre-push-hook-scan-scope`); `bin/romp-manager`'s `placementFromCgroup` login-session read and the gear's `staleWord` Default pick (#967); wording nits on the #964 docs pair and the #965 test tightenings. Build off upstream/main, since the wave-1 heads are not on fork main.

OFFERED 2026-09-07: offered upstream as their PR #971 (2026-09-07, label fix, head 7f238149). Five commits: the pre-push hook's remote exclusion and merge-parents scan with bats cases, `bin/romp-manager`'s cgroup placement `outside` state, the stale-settings toast's sentinel word, and the #964/#965 wording rider.

MERGED 2026-09-07: their PR #971 merged as-is (merge c351f336, head 7f238149); nothing to fold.
