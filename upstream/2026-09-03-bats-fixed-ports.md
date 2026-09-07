---
title: Upstream bats suites collide on FIXED ports on shared CI runners (`Address already in use` — the red check the maintainer reran past on his #897 merge); the fork already moved one such port (the romp-manager-ensure.bats hunk in fork commit `2b9c5e48`, deliberately left out of the busy-drain offer)
status: merged
where: fork commit `2b9c5e48` (partial: one file); a general free-port helper is not yet built
added: 2026-09-03
pr:
tier: tests-only
offered: their PR #951
closed: 2026-09-06
---
Flake class, not a logic bug: bats files bind fixed ports, and two suites (or two runners on one box) collide. Offer shape: a shared free-port helper in the bats support lib + migrate the fixed binds; the fork’s single-port move is the precedent. Test-only.

Status detail (migrated from the table): candidate

MERGED 2026-09-06T19:50Z via their PR #951 (merge `305171f6`), the bats tmux-socket isolation offer: its `tests/free-port.bash` helper (with `tests/free-port.bats`) is the shared free-port helper this entry asked for, and the offer migrated the fixed binds (five free-port cases in the 20000-24999 band per the maintainer's body corrections). The fork's single-port move in `2b9c5e48` was the precedent.
