---
title: The parked-op drain reports a refused effort level or fast toggle
status: merged
where: kernel/kernel.py _apply_pending_ops: the effort and fast arms read the setter's verdict and, on a refusal, write the drain refusal stderr line and send the chat a settingRefused frame (gesture command); tests/test_kernel_meta_command_gate.py RefusalReachesTheClient
added: 2026-09-18
pr:
tier: fix
offered: their PR #1865
closed: 2026-09-19
---
The parked-op replay dropped set_effort and set_fast verdicts, so a Codex effort pick parked mid-compaction and refused when the drain fired it (a level the model's catalog does not offer) was popped silently: no stderr line, no reply, and the queued chip retired as if the level had landed. The fork now reads the verdict in both arms and, on a refusal, writes the same pending ops apply refused line the command and compact arms write and sends the chat the settingRefused frame the live setEffort and setFast ops answer with; nothing applies before the gate lifts. Offered 2026-09-19 as their PR #1865, stacked on #1863.

2026-09-18: approved for offer by the user (batch 2 of the 2026-09-18 plan; his answer covers the fix and docs entries of batches 2 to 7, batch by batch, features excluded). Filed stacked on effort-refusal-setting-refused-frame (shared file kernel/kernel.py; it sends the same frame).

2026-09-19: offered as their PR #1865 (batch 2 of the 2026-09-18 plan, stacked on #1863); the project's reviewer pushed test-only fixes onto the branch the same night (the fast cases run as an SDK session, anticipating their #1864).

2026-09-19: merged upstream as their PR #1865 at 07:47:38Z (merge ba9321388); the row read offered until the stale check of 2026-09-21 found it
