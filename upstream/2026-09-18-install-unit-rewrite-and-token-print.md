---
title: install.sh writes the unit under a running manager and prints no token for an unserved dashboard
status: candidate
where: install.sh, bin/romp-service (the rewrite verb), tests/install-sh.bats, tests/install-optional-deps.bats, tests/romp-service.bats, docs/reference.md
added: 2026-09-18
pr:
tier: fix
offered:
closed:
---
Two findings of the box administrator's hazard review of the merged pull-in (2026-09-16). (1) install.sh skipped its whole service step when romp-service status said running (its 2026-07-21 guard against the macOS bootout), so a unit change a release carried, the MALLOC_ARENA_MAX=2 line the memory fix needs, never reached a box that installed while its manager ran, and the administrator added a drop-in by hand. A running manager now takes the new romp-service rewrite: the unit (the plist on macOS) is written whole, by rename, systemd is reloaded on Linux, nothing is restarted, and one line says the manager keeps its old unit until its next restart and names the command; a failed rewrite fails the run. (2) Under ROMP_NO_SERVICE the closing lines printed the dashboard URL with the serve token read from disk, a credential into the scrollback and every scripted install's log for a dashboard this run is not serving; that road now prints the bare URL and says romp url prints the token. Upstream ships both the skip and the print; an offer waits on the user's word.
