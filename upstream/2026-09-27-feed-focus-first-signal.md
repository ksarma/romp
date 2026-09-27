---
title: tests/test_feed_focus_latency_served.py: a tab change made in the chat moves the section in the task of the first of the two signals to reach the feed's page code (the shell's relay or the kernel's activeChat frame), before the animation frame after it; each order is forced, and the relay alone still moves the section when the kernel's frame is late or absent
status: candidate
where: tests/test_feed_focus_latency_served.py (DRIVER: the init script's message listener with the handoff:activeChat stamp and the two holds, setHoldRelay, setHoldFrame, waitFeedHop, roads d3_strip_click_kernel_frame_first and d4_strip_click_relay_first; FeedFocusLatencyServed._chat_side; FeedFocusLatencyServed.test_3c_whichever_signal_reaches_the_feed_first_moves_the_section, new); upstream/2026-09-27-feed-focus-first-signal.md (this entry)
added: 2026-09-27
pr:
tier: docs
offered:
closed:
---
The project's copy of the module has the same bound (its file differs from the fork's only in how it copies the built bundles), so the same race reds there: the chat sends its tab on its socket and posts it to the shell in the same call, and when the feed's shim hands the kernel's activeChat frame to the page code before the shell's relay task runs, the section moves in the shim's task and the old lower bound (relay <= head) fails by one 0.1 ms clock step although the section moved within the frame. Seen twice in local full sweeps of branches that do not touch the path; not reproduced in 20 runs of the module alone. The fix stamps the shim's handoff from the driver's capture listener (no product change), bounds the repaint by the first signal and the animation frame after it, and adds two forced-order roads: the kernel's frame first reds the old bound on every run and is green under the new one; the relay first is green under both and keeps the local signal's claim proven with the kernel's frame late. Tests only, so docs tier.
