---
title: The landing shim declares a redial only when its page may already hold sessions
status: candidate
where: kernel/kernel.py:50969 (the dial URL term), kernel/kernel.py:60238-60245 (the accept-time comment), tests/test_chat_skeleton_reconnect_gate.py (test_08, test_09), tests/test_pane_shim_return.py ReconnectFlag, tests/test_chat_skeleton_reconnect.py:423
added: 2026-09-10
pr:
tier: fix
offered:
closed:
---
Upstream https://github.com/romp-on/romp/pull/1017 sets everConnected at the first onopen and dials reconnect=1 on every redial, so a fresh page whose first socket died before its bundle loaded declares a redial for sessions it never held; upstream masks it with an unconditional pop at the bundle's ready, the fork's redial flag at accept did not, so the fold gates the term on bundleReady too. The gate is correct for upstream as well (a redial before the bundle evaluated holds nothing); the queued-ready residual is documented in the comment, not pinned.
