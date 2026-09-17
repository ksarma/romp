---
title: The dropped-sends notice card is never posted on the boot road: the kernel wires the backend's notice door after the constructor whose echo reseed posts the card
status: candidate
where: kernel/sdk_backend.py (SdkBackend.__init__ parks the reseed's cards in _boot_notices; _mark_dropped_echoes' park argument; post_boot_notices posts them on a thread of its own), kernel/kernel.py (_sdk_locked: the post_boot_notices call after the on_notice wiring); tests/test_restart_redelivery_stale.py::TheBootRoad
added: 2026-09-17
pr:
tier: fix
offered:
closed:
---
Upstream wires the notice door on the backend's class (type(_sdk_backend).on_notice = staticmethod(post_notice)) after SdkBackend's constructor returns, and the constructor runs _reseed_echoes, whose _mark_dropped_echoes flags every held human send older than REDELIVER_MAX_AGE_S dropped and stale and posts the dropped-sends card through post_notice, which resolves that door with getattr and finds none: the flags land on the mirror with no card, and the newly filter (not dropped) excludes the send on every later boot, so the card the re-delivery age line promises for a restart is posted only on the spawn road (a fresh CLI) and never on the boot road, the road a kernel restart takes. Hoisting the class assignment above the constructor deadlocks the boot: post_notice's session check falls to Sessions.live(), which re-takes the non-reentrant _sdk_lock the boot thread holds through the constructor. The fix parks the card POST (a zero-argument callable) during the reseed and keeps the flag writes, the queue re-add and the mirror write synchronous; the kernel calls post_boot_notices once the door is wired, and the backend posts on a thread of its own that waits the lock out, the shape the todo_lost seam already uses. The pin constructs a real SdkBackend over a reg carrying a stale human echo, wires the door the kernel's way after the constructor, and asserts exactly one post carrying the dropped-sends key and one card; it fails on upstream's order with no post at all. Found by the 2026-09-17 catch-up fold's kernel review (item 3).
