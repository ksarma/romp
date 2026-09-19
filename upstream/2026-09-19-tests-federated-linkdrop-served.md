---
title: A served lab drives a remote link dropping and returning mid-session against the per-connection reassembler
status: candidate
where: tests/test_federated_linkdrop_served.py (new: LinkProxy, LinkDropBothNew, LinkDropOldLocal)
added: 2026-09-19
pr: 857
tier: docs
offered:
closed:
---
The served witness for a remote link dropping mid-session against the reassembler fork PR 815 landed (merged as 9fec1eea6): two hermetic kernels, a TCP splice standing in for the hub forward, Chromium over the hub Waiting, Outline and feed pages, phases before the drop, on the socket the link return dialed and on the socket the hub restart dialed. At 815 head every redial is served a whole keyed feed first and every counter (delta-unapplied, feedDelta-unapplied, feedDelta-nobase, delta-unknown-slot, delta-unkeyed-base, asks) is zero. A knob-gated old-hub class mints a detached worktree at a main before 815 and records the storm there: 3 / 0 / 3 / 3 delta-unapplied rows across before, link down, after and the local restart, so the storm is gated on the link and a redial restarts it. Tests only; both classes skip as optional without their knobs.
