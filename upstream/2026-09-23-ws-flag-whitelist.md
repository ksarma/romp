---
title: The setSessionFlag socket op refuses a flag name outside the lane toggles, as POST /flag does, through one shared predicate, so a dashboard client can no longer set threadMail or the legacy postalOff on a session
status: candidate
where: fork branch `quickfix-ws-flag-whitelist`: `kernel/kernel.py` (`_lane_flag_refusal` beside `_LANE_FLAGS`, the `/flag` arm of `_state_write_route`, the `setSessionFlag` arm of `Handler._dispatch_ws`), `tests/test_obsidian_state_routes.py` (`SocketFlagWhitelist`, `FlagWriterPopulation` and its source walkers, the socket frame helpers), upstream/2026-09-23-ws-flag-whitelist.md (this entry)
added: 2026-09-23
pr:
tier: fix
offered:
closed:
---
The setSessionFlag socket op wrote any flag name an authenticated dashboard client sent, while POST /flag refused a name outside `_LANE_FLAGS` with a 400. So a client could set `threadMail` on a comment thread, the key that turns its mail on (fork PR #897 discloses what follows on the fork: the deadness mirror's roster then omits comment-thread sids that relay), or the legacy `postalOff`, which the kernel and the postal bus read as isolation. Upstream main carries the same arm and reads the same keys. Both doors now ask one predicate, `_lane_flag_refusal`, over the one list: the socket answers an unlisted name on the settingRefused frame with the route's sentence inside and `value` null, and writes nothing. No product surface sends a name outside the list (the lane gear's LANE_TOGGLES, the tab menu's typed union, the Obsidian panel's POST). Tests: the refusal executed through the real dispatcher and over a real socket to the served Handler, red before the fix (the store gained threadMail); the doors that write a session flag derived from the kernel's source and pinned as a set, each asking the predicate before its setter.
