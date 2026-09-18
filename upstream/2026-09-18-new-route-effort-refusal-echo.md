---
title: POST /new echoes a refused effort level as refused, never as applied
status: candidate
where: kernel/kernel.py _apply_new_session_prefs: the effort leg unpacks the setter's took and echoes effort only when it took, else a refused entry with the setter's words and one stderr line; bin/romp, romp new's echo reader: a refused echo prints one stderr line naming the asked level and the kernel's reason and keeps --effort out of the unacknowledged-ask warning; tests/test_new_route_prefs.py; tests/romp.bats
added: 2026-09-18
pr:
tier: fix
offered:
closed:
---
The POST /new per-spawn prefs pass (the create and the idempotent existing-open arm) discarded the _set_effort_or_park's verdict and echoed a refused Codex effort level back as applied, so romp new printed the level as applied and exited 0 while nothing changed. The fork now echoes effort only when the setter took it and otherwise answers a refused entry carrying the setter's own words, with one stderr line as the typed route writes. The offer waits on the user's word under the standing no-new-upstreaming rule.
