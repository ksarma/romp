---
title: bats isolation of the tmux socket directory: every suite that starts a real `bin/romp-manager`, or whose subject shells out to tmux, loads `tests/tmux-private.bash` (`TMUX_TMPDIR` under the test dir, created first because tmux 3.4 silently falls back to the default socket directory when it names a missing one; the private server killed in teardown through the real tmux, never a PATH mock). `romp-manager-ensure.bats` keeps its recording fake tmux on PATH for the whole file, and two tests pin the isolation: the `ensure`-spawned manager's tmux is handed the private directory and it already exists; with the real tmux, the server socket lands inside the test dir and the teardown kill reaches it.
status: merged
where: branch `batsisolate` (`tests/tmux-private.bash`, `tests/tmux-private.bats`, `tests/romp-manager-ensure.bats`, `tests/romp-manager-origin.bats`, `tests/romp.bats`, `tests/tmux-status-hook.bats`, `tests/README.md`)
added: 2026-09-06
pr:
tier: tests-only
offered: their PR #951
closed: 2026-09-06
---
Upstream's suite has the same hole: `romp-manager-ensure.bats` and `romp-manager-origin.bats` start a real manager with no tmux mock, so its startup `tmux start-server` runs on the developer's default socket. On 2026-09-06 a sweep did that ninety seconds after a stray kill-server had removed the default server, and for the rest of the day the machine's tmux server carried the sweep's environment inside the service's cgroup. Test-only; no product code.

Status detail (migrated from the table): **offered** — their PR #951 (2026-09-06), label `tests-only`

MERGED 2026-09-06T19:50Z as their PR #951 (merge `305171f6`), as offered; the body took the maintainer's corrections only (port band 20000-24999, five free-port cases, 402 tests). Its `tests/free-port.bash` helper also closed the fixed-ports entry (`bats-fixed-ports`).
