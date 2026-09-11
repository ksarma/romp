---
title: API health indicator: history on hover. The rail cell's hover and click detail gain a History section read from GET /api-health at show time (the shell's cookie auth, no poll, the frame unchanged): overall.state with its since and why, one row per window (attempts, 429 and 5xx shares, no-status attempts, give-ups, sessions that retried; an incomplete window says how long the kernel has been up), the newest six transitions with the state entered and how long it held, a kernel-restart row or divider (taking no slot) where the tail crosses bootAt, and a loud line when the read fails; focus shows the hover as a tooltip, blur or Escape hides it, a click pins it as the dialog
status: merged
where: kernel/kernel.py (_LANDING_APIH_JS: load, histHTML, descText, winRow, transRows, anchor, show, open, the cell's listeners; the tip stylesheet; _sdk_locked passes boot_at; the route serves the aggregator's bootAt), kernel/sdk_backend.py (SdkBackend boot_at, handed to ApiHealth; ApiHealth._seed truncates the stamp to the millisecond, clamps it past the restored tail and keeps it as boot_stamp, which snapshot() serves as bootAt; _row_ok requires a finite numeric t), docs/reference.md "The bottom bar's indicator" and the payload's bootAt field, docs/guide.md; tests tests/test_api_health_hover.py (since the 4d-4 fold also the home of the claims the fork's retired webview hover source-pin module pinned, that module deleted by the fold), tests/test_api_health_hover_browser.py, tests/test_api_health_rail.py (three pins rewritten), tests/test_kernel_auth_hardening.py (the bootAt/started assertion)
added: 2026-09-08
pr:
tier: feature
offered: their PR #1203
closed: 2026-09-09
---
Depends on two entries: 2026-09-02-api-health-signal (approved; the route it reads) and 2026-09-07-api-health-cell (candidate, fork PR #283; the _LANDING_APIH_JS, #rail-api cell and #ah-tip stylesheet every hunk here edits). Offer it after the cell entry or stacked on it: on a tree without the cell there is nothing for this diff to attach to. Reads the signal through the designed route, so it ports with them; nothing fork-specific beyond the salted labels the signal entry already flags.
