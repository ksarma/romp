---
title: romp down polls the manager past the kernels' SIGKILL grace
status: candidate
where: bin/romp: the down poll against bin/romp-manager SHUTDOWN_GRACE_MS
added: 2026-09-16
pr:
tier: fix
offered:
closed:
---
bin/romp-manager grants each kernel SHUTDOWN_GRACE_MS after its SIGTERM before the SIGKILL (8000 ms since the grace was raised from 5 s; ROMP_SHUTDOWN_GRACE_MS overrides it) and exits at that grace plus 200 ms at the latest, but `romp down` polled for it 28 times a quarter second (7 s nominal), so a kernel that used its exit budget made the down report a manager that would not stop, exit 1 and take the down marker back. The fork sizes the poll from the grace read the way the manager reads it (ROMP_SHUTDOWN_GRACE_MS, else 8000) plus a 2 s margin, at least 10 s; corrects the comment beside the poll that still said 5 s and the bin/README.md row; and pins it in tests/romp.bats with a real manager under a 12 s grace and a kernel that holds its SIGTERM for 11.5 s. Upstream bin/romp at 14f1548a9 carries the same loop and comment. Found by the pull-in review, 2026-09-16.
