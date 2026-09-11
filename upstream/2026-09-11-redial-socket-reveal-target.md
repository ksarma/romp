---
title: A tap after the chat pane redialed lands again: the redial's first tab strip stamps the pane ready and consumes the parked reveal
status: merged
where: kernel/kernel.py (_resolve_reconnect stamps ready; the three strip senders consume after _send_tab_order; _consume_pending_reveal why kwarg), tests/test_kernel_webpush.py (RevealAiming), tests/test_chat_skeleton_reconnect.py
added: 2026-09-11
pr:
tier: fix
offered: their PR #1383
closed: 2026-09-11
---
