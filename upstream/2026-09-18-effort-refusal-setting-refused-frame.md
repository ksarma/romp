---
title: A refused effort level or fast toggle is answered on the settingRefused frame, not a bare warn
status: merged
where: kernel/kernel.py: the setEffort and setFast ops in _drive and the effort, fast and unowned arms of _route_meta_command (the unowned arm: a session no running backend owns, refused before any setter, the flag from the command head) send type settingRefused, gesture command, sid, flag, text; ui/webview/render.ts: the settingRefused arm gesture command branch clears the chat's metaPending entry; tests/test_kernel_meta_command_gate.py, tests/test_sdk_registry_blind.py, tests/test_sdk_kernel.py, ui/webview/codex-meta-choices.test.ts
added: 2026-09-18
pr:
tier: fix
offered: their PR #1863
closed: 2026-09-19
---
The Codex effort refusal reached the client as a bare warn frame with no sid or type of its own: the chat read a warn arriving while a session create was in flight as that create's verdict and struck the provisional tab, and the timeline page renders no warn at all, so a lane-menu pick's refusal was dropped and its optimistic dim ran its 20 s timer, although both pages already handle a settingRefused frame for exactly this. The fork now answers from both roads (the setEffort op and the sendCommand route) with the timeline's existing settingRefused shape (gesture command, the sid, the flag effort or fast, the reason), moves the fast toggle refusal onto it, and gives the chat's settingRefused arm a gesture command branch that ends its own switching dots on the event. The fold's delta round moved the route's unowned arm onto the same frame too (a /model, /effort or /fast pick for a session no running backend owns, a dead Codex lane whose menu still offers its models: refused before any setter, the flag taken from the command head), so a dead lane's pick gets its reason where the owned arms give theirs. Offered 2026-09-19 as their PR #1863, stacked on #1862.

2026-09-18: approved for offer by the user (batch 2 of the 2026-09-18 plan; his answer covers the fix and docs entries of batches 2 to 7, batch by batch, features excluded). Filed stacked on clientdiag-reconnect-breadcrumb (shared file kernel/kernel.py), first of the three refusal entries because the other two send this frame.

2026-09-19: offered as their PR #1863 (batch 2 of the 2026-09-18 plan, stacked on #1862); the project's reviewer pushed a test-only fix onto the branch the same night (the fast cases run as an SDK session, anticipating their #1864).

2026-09-19: merged upstream at 06:57Z (9b89f091d) by the project's maintainer, after his own merge of main into the branch (2a074b414); the scaffold and branch pair are closed and deleted.
