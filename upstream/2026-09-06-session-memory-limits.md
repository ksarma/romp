---
title: Opt-in per-session memory limits on the transient scopes: `ROMP_CLI_SCOPE_MEMORY_MAX` / `_MEMORY_HIGH` / `_MEMORY_SWAP_MAX` (systemd sizes, validated; `MemoryMax=`, `MemoryHigh=`, `MemorySwapMax=` on the session's scope, with `OOMPolicy=continue` so one OOM kill takes the one process and not the whole scope) and `ROMP_CLI_SCOPE_OOM_SCORE_ADJ` (written to the session tree's `oom_score_adj` by the exec-in-place wrapper, so machine-wide killers prefer a session over the kernel). A value that does not parse is refused at the kernel's start and never reaches systemd-run; the wrapper's own check reports one with a third stderr form, `romp-cli-scope: ignored: …`, logged at arrival; the pre-flight carries the properties so an old systemd still launches the CLI, in its scope, without them. The kernel runs the wrapper's own steps once at its start (a probe scope with the properties, a memory-controller check inside it, the adjustment write in a throwaway child), so a value the machine refuses lands in `rejected` once instead of one `ignored:` line per launch, and a user manager without the memory controller (systemd accepts the properties and applies nothing) is a problem line. `/api-health` `cliScope` reports the values in force, `rejected`, `memoryControllerDelegated`, `unsettled` (the boot checks that did not answer) and `limitsIgnored`. Verified on systemd 255: a scope's default `OOMPolicy=stop` SIGTERMs the whole scope on one kill; `MemoryMax` alone lets the process swap out instead of dying on a box with swap; a user unit's `OOMScoreAdjust=` cannot go below the user manager's own value and the sessions inherit the kernel's anyway, so that lever does not separate them.
status: approved
where: fork PR #244 (branch `scopemem`, merged 2026-09-06): `bin/romp-cli-scope` (`preflight`, `size_ok`, `adj_ok`, `apply_adj`, `ignored`), `kernel/sdk_backend.py` (`CLI_SCOPE_LIMITS`, `cli_scope_limits`, `CLI_SCOPE_IGNORED_PREFIX`, `_note_cli_scope_ignored`, the `_options` overlay, `api_health_snapshot`), `docs/reference.md`; tests `tests/test_cli_scope.py`, `tests/romp-cli-scope.bats`, `tests/test_sdk_launch_error.py`
added: 2026-09-06
pr: 244
tier: feature
offered:
closed:
---
Motivated by 2026-09-06: a session's shell globbed a bloated `/tmp`, grew past 30 GB, and earlyoom killed the kernel as the largest process. Nothing is on by default; the docs carry a suggested setting for a shared machine. Depends on the per-session scopes (#194 on the fork).

Status detail (migrated from the table): candidate

APPROVED 2026-09-07: the fork owner said offer it (batch 13, tier feature — its dependency, the per-session scopes, merged upstream as their PR #953 on 2026-09-07T00:37Z, so it is offerable now. The `/api-health` `cliScope.rejected` surface depends on the API-health entry (`api-health-signal`); without it, carve that to a log line. The fake-`timeout` bats nit from the #953 review (`batch12-review-tests-only-followups`) touches `tests/romp-cli-scope.bats`).
