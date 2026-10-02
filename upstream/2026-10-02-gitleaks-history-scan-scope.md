---
title: tests/gitleaks-config.bats's history case scans the commits a branch adds over main, not all of history
status: candidate
where: tests/gitleaks-config.bats (history_scan_range, new; the history case, renamed and scoped by it; the section of cases on synthetic repositories, new); upstream/2026-10-02-gitleaks-history-scan-scope.md (this entry)
added: 2026-10-02
pr:
tier: docs
offered:
closed:
---
The history case ran gitleaks over all of HEAD's history (--log-opts="HEAD --diff-merges=first-parent"), so its cost grew with every commit. On a full clone of the fork's main at 13,762 commits it took 155 s on a development box at load 17, against the 180 s that CI's Run bats step allows a test (BATS_TEST_TIMEOUT). With its scope held to one core's worth of CPU it ran 293 s and bats marked it timed out. CI's Shell job checks out one commit, so there the case read the tip alone; CI's secret-scan job (fetch-depth: 0, --all) reads all of history on every PR and every push to main.

The fix is tests only. history_scan_range picks the range the case scans:
- <merge base>..HEAD over main, where main is origin/main when the clone has it, else a local main. --diff-merges=first-parent stays, so a merge on the branch is still read by its first-parent diff.
- The history the clone holds, with the reason printed, in a shallow clone, in a clone with no main ref, or for a HEAD that shares no commit with main.
- Nothing when HEAD is main or an ancestor of it: the case then skips with that statement instead of passing on a scan of no commits.
Seven new cases pin it on synthetic repositories; four of them run the history case end to end as a child bats. Tests only, so docs tier.

The project's public tree (upstream/main, last updated 2026-09-24) carries the same case in its tests/gitleaks-config.bats, with the same 180 s bound and the same one-commit checkout in its Shell job. An offer makes three edits:
- The comment above history_scan_range cites scripts/pr-orphans.sh and scripts/batch.py for the order main is read in. The project carries neither, so the offer states the order and its reason without them.
- history_case_over's comment cites tests/gitleaks-require.bats, which the project does not carry; drop the reference.
- The comment's cost figure is the fork's (13,762 commits). Restate it for the project's history or drop it.
