---
title: Feed: a second user gesture in one judge pass replays onto a fresh snapshot copy, never in place on the copy an earlier read served
status: offered
where: upstream branch feed-fresh-copy-offer: `kernel/kernel.py` `_feed_goals` (the json round-trip copy moved out of the punch guard; the guard keeps the counter once per session per pass); tests `tests/test_kernel.py` ViewBuilder (a new content-distinguishing case under a private sid; the flipped identity pin) and `tests/test_kernel_restore_flicker.py`
added: 2026-09-09
pr:
tier: fix
offered: their PR #1214
closed:
---
Audit row 15, filed alone: closes an aliasing hazard that renders no wrong card upstream today (build_feed is the only caller and nothing keys on the served object's identity) and prepares for a per-session feed memo, which would otherwise serve pre-gesture rows for the rest of a pass. The _feed_goals_view split, the live/snap counters and the _FeedSegs memo stay with the perf4-feed-memo candidate.
