---
title: A served lab drives a remote link dropping and returning mid-session against the per-connection reassembler
status: candidate
where: tests/test_federated_linkdrop_served.py (new: LinkProxy, LinkDropBothNew, LinkDropOldLocal), tests/test_federated_linkdrop_mint.py (OldHubMintIsPrivate), tests/test_federated_linkdrop_driver_bound.py (TheDriverEndsBeforeCI)
added: 2026-09-19
pr: 857
tier: docs
offered:
closed:
---
The served witness for a remote link dropping mid-session against the reassembler fork PR 815 landed (merged as 9fec1eea6): two hermetic kernels, a TCP splice standing in for the hub forward, Chromium over the hub Waiting, Outline and feed pages, phases before the drop, on the socket the link return dialed and on the socket the hub restart dialed. At 815 head every redial is served a whole keyed feed first and every counter (delta-unapplied, feedDelta-unapplied, feedDelta-nobase, delta-unknown-slot, delta-unkeyed-base, asks) is zero. A knob-gated old-hub class mints a private clone of the repository (git clone --shared, checked out detached at a main before 815) under its scratch, registering nothing in the clone it runs from, and records the storm there as an invariant: one delta-unapplied row per feed slot patch the Outline received, pinned by rev per window and over the drive (3 / 0 / 3 / 3 across before, link down, after and the local restart in most recorded drives; 3 / 0 / 1 / 3 in a reviewer drive at round 1's head and 0 / 0 / 3 / 3 in three builder drives, the round-3 head, a 30 s-dwell drive and the round-5 head on 2026-09-20, where a churned socket's whole frame absorbed phase A after its last notice was posted, the one event that excuses an empty phase), zero with a change due while the link was down and the while-down read taken twice the drive's slowest link-up delivery after the post, so the storm is gated on the link and a redial restarts it. Tests only; LinkDropBothNew runs wherever the served labs run, CI served job included, and the old-hub class skips as optional without its knobs, the skip reason naming what goes unexecuted.
