---
title: Batch-12 review tests-only follow-ups, one bundle: nine small test edits the maintainer's merge comments named
status: approved
where: not built; from the maintainer's review comments on their PRs #941, #943, #944, #946, #947, #948, #949, #953 and #957 (2026-09-06/07); build off upstream/main, since those heads are not on fork main: `tests/test_tempdir_hygiene.py`, `tests/test_sdk_lifecycle_hardening.py`, `tests/test_session_move_live.py`, `tests/test_judge.py`, `tests/test_model_versions.py`, `tests/test_dead_wait_block.py`, `ui/webview/pane-shim-stale.test.ts`, `ui/webview/github-link.test.ts`, `tests/romp-cli-scope.bats`
added: 2026-09-07
pr:
tier: tests-only
offered:
closed:
---
Nine reviewer-requested test tightenings from the merged batch: `test_tempdir_hygiene`'s `__main__` path imports the `tests` package (else the hook assertion fails and two scratch dirs leak); the lifecycle-hardening header stops claiming `ps` is patched in every test (two PsArgv tests run the real one); the live session-move test gets a comment at the assertion about child stderr carrying helper diagnostics and an always-run test for `_api_key_helper` precedence and the `CLAUDE_CONFIG_DIR` default; `IndexTierLever` and `EffortCapability` setUps clear `_ALIAS_SERVED`; `test_model_versions` wraps the cold `_learned_versions()` call in `_counting_reg_reads`; the dead-wait mid-pass test's comment names the single-flight guard, not the sweep skip; `pane-shim-stale` pins the `foreground-quiet` why; `github-link` asserts exactly one re-ask per reconnect; `romp-cli-scope.bats` fakes `timeout(1)` exiting 124 instead of spending a real 10 s.

APPROVED 2026-09-07: the fork owner said offer it (batch 13, tier tests-only). Fork side, open fork PR #276 rewrites every test module's loading, so land after it or rebase onto it; the `_ALIAS_SERVED.clear()` part may ride the `_note_served_model` entry (`note-served-model-no-modelusage`) instead, and the bats part touches the memory-limits entry's test file.
