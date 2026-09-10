---
title: Chat tabs: the no-strip ready holds for feed and timeline clients too (executing cases per app), and the living-only ordered reader _ordered_alive goes
status: offered
where: kernel/kernel.py (_ordered_alive removed, _tab_order_frame docstring), tests/test_kernel_tabs_first.py, tests/test_kernel.py, tests/test_kernel_order.py, tests/test_tag_edit_ack.py
added: 2026-09-10
pr:
tier: fix
offered: their PR #1240
closed:
---
Follow-up the post-merge record on their #1218 filed: the no-strip ready was pinned for a chat client only and the reader the removed strip was built from stayed defined with no caller. Filed from #1218's head (now on main).
