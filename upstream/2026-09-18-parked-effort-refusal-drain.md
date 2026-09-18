---
title: The parked-op drain reports a refused effort level or fast toggle
status: approved
where: kernel/kernel.py _apply_pending_ops: the effort and fast arms read the setter's verdict and, on a refusal, write the drain refusal stderr line and send the chat a settingRefused frame (gesture command); tests/test_kernel_meta_command_gate.py RefusalReachesTheClient
added: 2026-09-18
pr:
tier: fix
offered:
closed:
---
The parked-op replay dropped set_effort and set_fast verdicts, so a Codex effort pick parked mid-compaction and refused when the drain fired it (a level the model's catalog does not offer) was popped silently: no stderr line, no reply, and the queued chip retired as if the level had landed. The fork now reads the verdict in both arms and, on a refusal, writes the same pending ops apply refused line the command and compact arms write and sends the chat the settingRefused frame the live setEffort and setFast ops answer with; nothing applies before the gate lifts. The offer waits on the user's word under the standing no-new-upstreaming rule.

2026-09-18: approved for offer by the user (batch 2 of the 2026-09-18 plan; his answer covers the fix and docs entries of batches 2 to 7, batch by batch, features excluded).
