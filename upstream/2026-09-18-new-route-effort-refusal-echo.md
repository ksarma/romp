---
title: POST /new echoes a refused effort level as refused, never as applied
status: merged
where: kernel/kernel.py _apply_new_session_prefs: the effort leg unpacks the setter's took and echoes effort only when it took, else a refused entry with the setter's words and one stderr line; bin/romp, romp new's echo reader: a refused echo prints one stderr line naming the asked level and the kernel's reason and keeps --effort out of the unacknowledged-ask warning; tests/test_new_route_prefs.py; tests/romp.bats
added: 2026-09-18
pr:
tier: fix
offered: their PR #1872
closed: 2026-09-19
---
The POST /new per-spawn prefs pass (the create and the idempotent existing-open arm) discarded the _set_effort_or_park's verdict and echoed a refused Codex effort level back as applied, so romp new printed the level as applied and exited 0 while nothing changed. The fork now echoes effort only when the setter took it and otherwise answers a refused entry carrying the setter's own words, with one stderr line as the typed route writes. Offered 2026-09-19 as their PR #1872, stacked on #1865.

2026-09-18: approved for offer by the user (batch 2 of the 2026-09-18 plan; his answer covers the fix and docs entries of batches 2 to 7, batch by batch, features excluded). Filed stacked on parked-effort-refusal-drain (shared file kernel/kernel.py; it shares the frame's wording).

2026-09-19: offered as their PR #1872 (batch 2 of the 2026-09-18 plan, stacked on #1865).

2026-09-19: merged upstream at 08:21Z (662678ebc) by the project's maintainer; the scaffold and branch pair are closed and deleted.
