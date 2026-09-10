---
title: Backend labels a person reads follow the T288 rule everywhere
status: candidate
where: kernel/kernel.py 17561, 18706, 18759, 19239, 52005, 56926; kernel/sdk_backend.py 2832-2834, 8120, 11741, 11746; docs/reference.md 145, 146, 147, 153, 520, 595-597, 2282; ui/webview/backend-names.test.ts (the retired phrases), kernel/kernel.py:52998, bin/romp:679, bin/romp:3013, bin/romp:3019, bin/romp:3024, bin/romp-sdk-setup:141, docs/reference.md:585-587, docs/reference.md:2337, tests/romp.bats:243, tests/romp.bats:1189, tests/romp.bats:3271, tests/romp.bats:3379, tests/romp.bats:3382, tests/test_api_health_hover_browser.py:412, tests/test_api_health_hover_browser.py:821
added: 2026-09-10
pr:
tier: fix
offered:
closed:
---
Upstream https://github.com/romp-on/romp/pull/1199 renamed the SDK and tmux labels a person reads to Claude Code and Claude Code (tmux), but these user-facing strings kept the old words. The fold renamed them with the docs, and ui/webview/backend-names.test.ts now pins the retired phrases in kernel/kernel.py and kernel/sdk_backend.py. kernel/kernel.py:52998, docs/reference.md:2337 and tests/test_api_health_hover_browser.py:412 and :821 (the api-health hover's tmux count) are absent at the fold tip 459e50d6 but reached upstream with their PR 1197 (merge c830620a, after the tip) carrying the old wording, so they are shared going forward and stay in where:.

Remaining after the fold (shared with upstream verbatim, left for this offer to carry as one PR with the test):
bin/romp help rows 670, 675, 676, 677, 678 and 708 ("SDK by default", "for the SDK session", "running SDK session's",
"Move an SDK session's"), bin/romp 2994 ("--model/--effort need an SDK session"; no pin), bin/romp 1833, 1888 and 2373
("romp SDK session"; 2373 pinned by tests/romp-headless.bats:82), bin/romp 3147-3148 ("(SDK session, working in ...)"),
bin/romp-sdk-setup 231 ("only the SDK backend (plain romp new) is disabled."), kernel/session_backend.py 218 and 222
(the base-class MCP status and MCP controls replies a Claude Code (tmux) session returns and the MCP panel shows a
person: "MCP status is available on SDK sessions; this one runs in a terminal" and its controls twin; rename "SDK
sessions" to "Claude Code sessions" beside the sdk_backend.py MCP replies this entry already renamed; no pins),
docs/read-side.md 219 and 221 (the delivery-leg labels "**SDK session**" and "**tmux session on Claude Code ...**"),
docs/reference.md 2053 ("SDK-backed sessions", the sdkSessionsLive gloss), 2057 and 2156 ("tmux-backed sessions").
docs/reference.md 1271 ("an SDK-driven CLI") and docs/read-side.md 345 ("an SDK send") describe the Agent SDK
mechanism and stay by rule. The KINDLBL sdk chip at kernel.py 51992 is a deliberate exception, not an identifier: its
value "sdk" is rendered text (the Log popover's filter chip and every sdk entry's chip; pinned by
tests/test_sdk_error_visibility.py:203), but the chip names the Agent SDK as software, the layer whose errors those
entries report, and the value is the kind key mirrored in ui/webview/badge-mirror.ts (kind: "sdk"), so it stays; the
tooltip beside it (52005) already says the Claude Code backend. The renamed phrases are pinned by
ui/webview/backend-names.test.ts over both kernel files, so the test edit travels with the renames, never alone.

Fork-only copy of the same class, absent from upstream's tree and renamed in the fold (not this offer's to carry):
bin/romp 3001 ("--env/--no-env need a Claude Code session", pinned by tests/romp.bats:3396), docs/install.md 30 ("the
Claude Code backend's venv") and 38 ("every Claude Code session then fails"). docs/install.md 19, 38, 41 and 43 ("the
SDK venv") name the Agent SDK's venv and stay.
