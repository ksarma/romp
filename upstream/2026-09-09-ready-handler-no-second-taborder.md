---
title: Chat tabs: ready sends no tab strip of its own; the connect push's strip is the one source and ready clears its slot
status: offered
where: upstream branch ready-taborder-offer, re-derived onto their #1017 from fork commit 6c2bb909: `kernel/kernel.py` (the ready arm's second tabOrder frame removed; `_client_reset_chat_base` pops the taborder slot; docstrings), tests `tests/test_tag_edit_ack.py` ReadyStripSource (three red-first cases on the real dispatcher), `tests/test_kernel_tabs_first.py`, `tests/test_chat_skeleton_reconnect.py`, `tests/test_timeline_views.py`
added: 2026-09-09
pr:
tier: fix
offered: their PR #1218
closed:
---
Audit row 7. The ready handler's own tabOrder frame listed living sessions only while the connect push listed the kept-open read-only tabs too, so every page load closed those tabs until the pusher's next cycle; since #1017 routed that frame through the dedup slot, a socket served a strip before its bundle listened got no strip at ready at all. The connect push's frame is now the one source and ready clears the slot. The fork's collapse guard and ready gate stay separate.
