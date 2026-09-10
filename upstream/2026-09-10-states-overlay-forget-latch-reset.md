---
title: Awaiting overlay: a departed session's unreadable states file is named once per episode (the forget no longer discards the once-per-episode latch; the latch set is cleared whole above 256 paths)
status: offered
where: kernel/kernel.py (_states_overlay_forget, _states_overlay_on), tests/test_states_overlay_fold.py (three tests replacing the one that pinned the discard)
added: 2026-09-10
pr:
tier: fix
offered: their PR #1252
closed:
---
Defect in the review-fix commit 21de3fc1 inside their #1228 (our tick-tail memos offer): the forget discarded a departed sid's latch entry while build_session, loadOlder and GET /classify still read its file, so the unreadable line repeated once per rebuild. Upstream-native; filed directly from the upstream base.
