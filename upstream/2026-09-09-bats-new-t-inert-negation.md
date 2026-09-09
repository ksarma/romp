---
title: The `new -t` refusal test in tests/romp.bats checks no-new-session with a bare mid-test `! grep`, inert under bats errexit; the fork arms it
status: candidate
where: tests/romp.bats, the `new -t` refusal test
added: 2026-09-09
pr:
tier: docs
offered:
closed:
---
Found resolving fold slice 2 (fork PR #451): upstream #1128 added four `! grep` lines to tests/romp.bats, and the check `! grep -q 'new-session' "$MOCK_LOG"` in the `new -t` leftover-key refusal test (upstream 7ffb4ea6:996) sits mid-test and is inert under bats errexit upstream (a bare `!` pipeline is exempt from `set -e` unless it is the test's final command; the other three lines are their tests' last commands and do assert). The fork arms it in its run-then-status form (`run grep -q 'new-session' "$MOCK_LOG"` then `[ "$status" -ne 0 ]`, tests/romp.bats:1403-1404) under its standing scanner rule (tests/test_bats_bare_negation.py, fork fe0f967f). The 2026-08-07 entry upstream/2026-08-07-bats-negated-grep-assertions.md records the rule (merged upstream as their #383); this entry is the slice's residual: upstream's main still carries the inert line.
