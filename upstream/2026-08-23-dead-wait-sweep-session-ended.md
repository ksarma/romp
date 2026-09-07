---
title: The dead-wait sweep (their #550) files its irreversible "session ended while still waiting" block off ONE raw liveness-listing miss — `_dead_wait_sweep`'s transition diff and `_wake_goal`'s dormant branch both convert a stamped Working card on bare absence from the merged map (a transient tmux list collapse or a swallowed SDK live-merge exception both empty it for a cycle), and nothing lifts the false block when the listing returns; on a tmux-less box the dormant branch takes every file-derived session, alive included
status: merged
where: fold-review fix in `upfold0823`: `_dead_wait_corroborated` (SDK reg alive-bit / standing death record / owner scan; unconfirmable → stand down with the transition kept armed, retried next tick) threaded through both writers
added: 2026-08-23
pr:
tier:
offered: their PR #574
closed: 2026-08-23
---
MERGED as-is (head is an ancestor of their main, verified same day). Branch retired. OFFERED 2026-08-23 (branch `deadwait-probe`, `01d0ec06` off tip `147678b1`, one commit — the finished two-round mechanism): docstrings anchor to their own _death_sweep_tick doctrine; _end_on_idle_sweep flagged in the body as follow-up, not patched; red-first 11/12 new tests fail on base; review clean, scaffold CI green (since-closed fork #108). Their sweep has the same hole verbatim, and the fix is their own corroboration doctrine threaded through — their `_death_sweep_tick` already asks `TmuxBackend.alive_sids` and stands down on a failed probe before stamping; the dead-wait writers just never did. The tri-state helper here (`_dead_wait_corroborated`, modeled on the fork's `_confirmed_ended`) is small and would travel with an offer; note their `_end_on_idle_sweep` also spends requests on the same raw `tmux.get() is None` read (a second beneficiary if offered). Pinned red-first in tests/test_dead_wait_block.py.

Status detail (migrated from the table): ✅ **merged** — their PR #574, merged as-is 2026-08-23 (merge `36c41c95`)
