---
title: Backend labels a person reads follow the T288 rule everywhere
status: candidate
where: kernel/kernel.py 17561, 18706, 18759, 19239, 52002, 56923; kernel/sdk_backend.py 2832-2834, 8120, 11741, 11746; docs/reference.md 145, 146, 147, 153, 520, 595-597, 2282; ui/webview/backend-names.test.ts (the retired phrases), kernel/kernel.py:52995, bin/romp:679, bin/romp:3013, bin/romp:3019, bin/romp:3024, bin/romp-sdk-setup:141, docs/reference.md:585-587, docs/reference.md:2337, tests/romp.bats:243, tests/romp.bats:1189, tests/romp.bats:3271, tests/romp.bats:3379, tests/romp.bats:3382, tests/test_api_health_hover_browser.py:412, tests/test_api_health_hover_browser.py:821
added: 2026-09-10
pr:
tier: fix
offered:
closed:
---
Upstream https://github.com/romp-on/romp/pull/1199 renamed the SDK and tmux labels a person reads to Claude Code and Claude Code (tmux), but these user-facing strings kept the old words. The fold renamed them with the docs, and ui/webview/backend-names.test.ts now pins the retired phrases in kernel/kernel.py and kernel/sdk_backend.py.

Remaining after the fold (shared with upstream verbatim, left for this offer to carry as one PR with the test):
bin/romp help rows 670, 675, 676, 677, 678 and 708 ("SDK by default", "for the SDK session", "running SDK session's",
"Move an SDK session's"), bin/romp 2994 and 3001 (pinned by tests/romp.bats:3396), bin/romp 1833, 1888 and 2373 ("romp SDK
session"; 2373 pinned by tests/romp-headless.bats:82), bin/romp 3147-3148 ("(SDK session, working in ...)"),
bin/romp-sdk-setup 231 ("only the SDK backend (plain romp new) is disabled."), docs/reference.md 2053 ("SDK-backed
sessions", the sdkSessionsLive gloss), 2057 and 2156 ("tmux-backed sessions"). The KINDLBL sdk kind key at kernel.py 51990
and its ui/webview/badge-mirror.ts twin are identifiers, not copy, and stay. The renamed phrases are pinned by
ui/webview/backend-names.test.ts over both kernel files, so the test edit travels with the renames, never alone.
