---
title: Upstream bats suites collide on FIXED ports on shared CI runners (`Address already in use` — the red check the maintainer reran past on his #897 merge); the fork already moved one such port (the romp-manager-ensure.bats hunk in fork commit `2b9c5e48`, deliberately left out of the busy-drain offer)
status: candidate
where: fork commit `2b9c5e48` (partial: one file); a general free-port helper is not yet built
added: 2026-09-03
pr:
tier:
offered:
closed:
---
Flake class, not a logic bug: bats files bind fixed ports, and two suites (or two runners on one box) collide. Offer shape: a shared free-port helper in the bats support lib + migrate the fixed binds; the fork’s single-port move is the precedent. Test-only.

Status detail (migrated from the table): candidate
