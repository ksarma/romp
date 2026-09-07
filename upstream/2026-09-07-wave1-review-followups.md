---
title: Wave-1 review follow-ups: pre-push hook new-ref exclusion and merge second-parent scan; manager placementFromCgroup login-session read; gear staleWord Default pick; #964/#965 wording nits
status: candidate
where: not built yet; branch wave1-review-followups-offer in progress (2026-09-07); from the maintainer's comments on #968, #967, #964, #965
added: 2026-09-07
pr:
tier: fix
offered:
closed:
---
Four parts from the maintainer's merge comments on the wave-1 PRs, built as one fix PR: the pre-push hook's new-ref exclusion and merge second-parent scan (#968, entry `pre-push-hook-scan-scope`); `bin/romp-manager`'s `placementFromCgroup` login-session read and the gear's `staleWord` Default pick (#967); wording nits on the #964 docs pair and the #965 test tightenings. Build off upstream/main, since the wave-1 heads are not on fork main.
