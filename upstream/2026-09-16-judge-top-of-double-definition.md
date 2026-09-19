---
title: judge.py defines _top_of twice; the None-returning first body is dead
status: merged
where: kernel/judge.py (the second _top_of above _demote_session_mints, removed on the fork; the survivor beside _sealed_above; the _demote_session_mints nest), tests/test_judge_top_of.py
added: 2026-09-16
pr:
tier: fix
offered: their PR #1855
closed: 2026-09-19
---
Upstream's T319 origin rule (romp-on/romp#1367, 2026-09-10) added a second module-level _top_of above _demote_session_mints that returns None when a parent chain dead-ends; the closer helpers' older _top_of below it returns the last id reached, and Python binds that later definition, so the first never ran and every T319 caller sees the id-returning body. On a node whose ancestor a rewind swept the top is the dangling parent id: _delegator_of, block_addressee_via, _block_peer_edge and the split op in apply_group guard the result and read it as no top; _demote_session_mints assigns it to parent and dereferences nodes[p] for a process mint whose seam top, target or recorded placement sits under such a chain, a KeyError where the body it was written against would have nested the step under the reply's ask or the nearest open top, or filed nothing. The fork removed the dead first definition in the stage 1 pull-in of 14f1548a9 (the kernel area's review round 1, item 5) and pins the bound body and its callers in tests/test_judge_top_of.py; the offer is the same deletion plus upstream's call on the _demote_session_mints arm (read the dangling id as no placement, or keep the loud KeyError).

2026-09-18: approved for offer by the user (batch 1 of the 2026-09-18 plan).

2026-09-19: offered as their PR #1855 (batch 1 of the 2026-09-18 plan); merged upstream 2026-09-19 00:12Z (e862e8f24).
