---
title: install.sh writes the unit under a running manager and prints no token for an unserved dashboard
status: candidate
where: install.sh, bin/romp-service (the rewrite verb), bin/README.md, kernel/kernel.py (_NO_RESTART_ACTIONS, _is_primary_kernel, _run_update), bin/romp-manager (specEnv's ROMP_KERNEL_ID), tests/install-sh.bats, tests/install-optional-deps.bats, tests/romp-service.bats, tests/test_restart_cuts.py, tests/test_kernel_update.py, tests/manager-registry.test.js, docs/reference.md
added: 2026-09-18
pr:
tier: fix
offered:
closed:
---
Two findings of the box administrator's hazard review of the merged pull-in (2026-09-16). (1) install.sh skipped its whole service step when romp-service status said running (its 2026-07-21 guard against the macOS bootout), so a unit change a release carried, the MALLOC_ARENA_MAX=2 line the memory fix needs, never reached a box that installed while its manager ran, and the administrator added a drop-in by hand. A running manager now takes the new romp-service rewrite: the unit (the plist on macOS) is written whole, by rename, systemd is reloaded on Linux, nothing is restarted, and one line says the manager keeps its old unit until its next restart and names the command; a failed rewrite fails the run. (2) Under ROMP_NO_SERVICE the closing lines printed the dashboard URL with the serve token read from disk, a credential into the scrollback and every scripted install's log for a dashboard this run is not serving; that road now prints the bare URL and says romp url prints the token. Upstream ships both the skip and the print; an offer waits on the user's word. Round 1 of the review (2026-09-18): the rewrite keeps the unit's own identity (ExecStart, ROMP_DIR, PATH, the service.env path, the instance lines) and refuses on a differing value; its audit row is written after the checks and is in the kernel's no-restart set, since the row read as the restart request behind any SIGTERM within ninety seconds of a deploy; the self-update's child carries no instance port or Claude config dir and runs from the primary kernel only (the manager hands each kernel its id); after the reload the rewrite reads NeedDaemonReload back.
