---
title: The boot orphan reaper (`find_orphan_clis`) matched nothing under systemd: it called a CLI orphaned only at ppid 1, but `systemd --user` is a child subreaper, so an orphaned SDK CLI re-parents to the user manager's pid — the reap matched nothing on Linux under the service, and only the unit's default KillMode=control-group had been killing those orphans on service restarts; now orphaned = an SDK-driven CLI holding one of our sids whose PARENT is not a live romp kernel (`_is_kernel_cmd` on the parent's `ps` text)
status: offered
where: fork branch `scopes`: `kernel/sdk_backend.py` (`find_orphan_clis`, `_is_kernel_cmd`); tests in `tests/test_sdk_lifecycle_hardening.py` (FindOrphanClis)
added: 2026-09-05
pr:
tier: fix
offered: their PR #941
closed:
---
OFFERED 2026-09-06 (branch `orphan-reaper`, `509c3f11` off tip `2b9db2be`, two commits carved from the fork’s scopes branch); scaffold CI green after one flake rerun (since-closed fork #204). Upstream ships the same ppid==1 matcher and the same Linux systemd install (`romp-service`), so the same miss: a hard-killed kernel's CLI keeps writing the transcript until the next service restart. Independent of the scopes work (worth offering on its own, and it is a prerequisite for offering the scopes, which remove the cgroup-kill cover). Verified on a Linux box 2026-09-05: an orphan from the service cgroup and from a transient scope both get ppid = the `systemd --user` pid. Pure on the `ps -axwwo pid=,ppid=,command=` text (`-ww`, or procps truncates each line to an exported `$COLUMNS` and the sid, 2 KB into the argv, is cut off); the fixtures that encoded ppid 1 gained the kernel's own line.

Status detail (migrated from the table): **offered** — their PR #941 (2026-09-06), label `fix`
