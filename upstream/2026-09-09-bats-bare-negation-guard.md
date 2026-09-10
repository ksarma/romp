---
title: Tests: a bare negation in a bats test is refused unless it is the test's last command; three inert sites armed
status: merged
where: upstream branch bats-negation-guard-offer: new `tests/test_bats_bare_negation.py` (a stdlib line scan over every tests/*.bats), and the armed sites in `tests/romp-headless.bats`, `tests/romp.bats`, `tests/tmux-status-hook.bats`
added: 2026-09-09
pr:
tier: docs
offered: their PR #1223
closed: 2026-09-10
---
Audit row 16. Upstream accepted this class twice (#383, #403) and re-grew three inert mid-test bare negations; the ratchet fails naming each file:line and the three sites are rewritten to run plus a status check. The tests-only hunk of the closed #1010, re-offered alone.
