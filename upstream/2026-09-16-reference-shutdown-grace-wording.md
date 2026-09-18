---
title: docs/reference.md's romp down and restart passages still give the manager a five-second SIGKILL grace and the poll a seven-second bound; the manager grants 8 s since 487b4a418
status: approved
where: docs/reference.md: the romp down passage and What survives a restart
added: 2026-09-16
pr:
tier: docs
offered:
closed:
---
Upstream raised bin/romp-manager's SHUTDOWN_GRACE_MS from 5 s to 8 s in 487b4a418 (an ancestor of the pinned tip 14f1548a9) with no doc edit: at the tip docs/reference.md's `romp down` passage still bounds the manager poll at seven seconds over a five-second grace, and What survives a restart says a kernel still running five seconds after the manager's SIGTERM gets SIGKILL. The fork's stage 1 pull-in (the rest area's review round 1, item 2) rewrites both passages to the manager's grace (`SHUTDOWN_GRACE_MS`, 8 s unless `ROMP_SHUTDOWN_GRACE_MS` says otherwise) plus a margin for its exit, in the words bin/romp's poll fix (upstream/2026-09-16-romp-down-polls-past-the-kill-grace.md) and bin/README.md's romp-manager row use, so the three surfaces agree; the nearby three-second kernel-probe sentence stays, it matches the pre-SIGTERM poll. The offer is the two passages on upstream's file, beside the bin/romp poll fix.

2026-09-18: approved for offer by the user (batch 4 of the 2026-09-18 plan; his answer covers the fix and docs entries of batches 2 to 7, batch by batch, features excluded).
