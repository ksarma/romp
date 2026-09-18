---
title: A refused effort level or fast toggle is answered on the settingRefused frame, not a bare warn
status: candidate
where: kernel/kernel.py: the setEffort and setFast ops in _drive and the effort, fast and unowned arms of _route_meta_command (the unowned arm: a session no running backend owns, refused before any setter, the flag from the command head) send type settingRefused, gesture command, sid, flag, text; ui/webview/render.ts: the settingRefused arm gesture command branch clears the chat's metaPending entry; tests/test_kernel_meta_command_gate.py, tests/test_sdk_registry_blind.py, tests/test_sdk_kernel.py, ui/webview/codex-meta-choices.test.ts
added: 2026-09-18
pr:
tier: fix
offered:
closed:
---
The Codex effort refusal reached the client as a bare warn frame with no sid or type of its own: the chat read a warn arriving while a session create was in flight as that create's verdict and struck the provisional tab, and the timeline page renders no warn at all, so a lane-menu pick's refusal was dropped and its optimistic dim ran its 20 s timer, although both pages already handle a settingRefused frame for exactly this. The fork now answers from both roads (the setEffort op and the sendCommand route) with the timeline's existing settingRefused shape (gesture command, the sid, the flag effort or fast, the reason), moves the fast toggle refusal onto it, and gives the chat's settingRefused arm a gesture command branch that ends its own switching dots on the event. The fold's delta round moved the route's unowned arm onto the same frame too (a /model, /effort or /fast pick for a session no running backend owns, a dead Codex lane whose menu still offers its models: refused before any setter, the flag taken from the command head), so a dead lane's pick gets its reason where the owned arms give theirs. The offer waits on the user's word under the standing no-new-upstreaming rule.
