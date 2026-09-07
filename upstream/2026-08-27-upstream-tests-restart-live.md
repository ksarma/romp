---
title: Upstream's own test suite restarts a LIVE deployment: their `tests/conftest.py` has no `ROMP_MANAGER_PORT` floor, so `ServeSecurity.test_restart_endpoint_acks_post` (pop/restore around a real `POST /restart`) races the ack against the restored live port and wins — three real kernel restarts fired on this box 2026-08-26/27 from full suite runs in upstream-tree worktrees
status: merged
where: fork `tests/conftest.py:25-40` (the two-part floor from fork PR #87: import-time poison + autouse re-assert, because module-level pops during collection erase import-time floors)
added: 2026-08-27
pr: 87
tier:
offered: their PR #737
closed: 2026-08-27
---
MERGED as-is (head is an ancestor of their main, verified same night). Branch retired. OFFERED 2026-08-27 as the suite-side half of the restart-race pair (branch `restart-race`, `a133665b`): the two-part floor + the test_restart_audit pop→write conversion + the lab.sh rider. Full suite 5756 green with the floor; scaffold CI green (since-closed fork #123). Found by the general session's 2026-08-27 restart forensics after this session's offer-worktree pytest runs kept restarting the live kernel. The offer is the fork's guard shape re-derived for their conftest. Same-class latent: `tools/romp-lab/lab.sh` never poisons the port (worth a sentence in the PR body).

Status detail (migrated from the table): ✅ **merged** — their PR #737 (commit 2 of the pair), merged as-is 2026-08-27 (merge `b264635b`)
