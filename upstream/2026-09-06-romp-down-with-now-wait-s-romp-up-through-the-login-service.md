---
title: `romp down` (with `--now` / `--wait <s>`), `romp up` through the login service, `romp status` naming a deliberate stop: the kernel is stopped THROUGH its supervisor (`romp-service stop`: `systemctl --user stop` / `launchctl bootout`; the manager's own `/stop` only when no service is installed) after a bounded quiesce through a new kernel route (`POST /down`: new turn starts and session creates held on the existing drain lease, extended to cover the wait plus a grace; blocks until the in-flight count is 0 or `wait` runs out; answers what a stop cuts; `{"cancel": true}` releases); a `down-by-romp` marker under the state root makes the stop deliberate to everything else (`romp status` exit 0 with the time, `romp-service status`, `romp-manager ensure` refusing to auto-start, `up` clearing it); the restart-audit row names the action so the cut ledger records a `down`
status: candidate
where: fork branch `rompdown` (bin/romp `down`/`up`/`status` + `_romp_restart_audit`, bin/romp-service `stop`/`start` + `ROMP_SYSTEMCTL`, bin/romp-manager `ensureDecision`/`clearDownMarker`, kernel/kernel.py `/down` + `_going_down`, kernel/sdk_backend.py `quiesce`/`quiescing`/`cancel_quiesce`/`inflight_names`)
added: 2026-09-06
pr:
tier:
offered:
closed:
---
(the user 2026-09-06, who wanted an easy, safe way to pause or stop the kernel.) Pure feature on surfaces upstream ships too (the manager, romp-service, the drain lease, the boot reconcile); nothing fork-specific in it. Tests: tests/test_kernel_down.py, tests/test_deploy_drain.py (GoingDownHold), tests/romp.bats, tests/romp-service.bats, tests/romp-manager-ensure.bats, tests/manager-down.test.js. Design points for the offer: the stop goes through the supervisor (a self-exit is a crash to Restart=always / KeepAlive); the quiesce is a lease, never a latch (the T121 rule); `romp status` exits 0 for a deliberate stop so a health check does not alarm; no pause mode — the drain lease gates SDK turn starts only (judges, tmux and Codex sessions run on), so a true pause is a follow-up needing gates in the pusher's starters and a visible dashboard state.

Status detail (migrated from the table): **candidate**
