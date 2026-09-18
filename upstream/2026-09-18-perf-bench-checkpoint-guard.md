---
title: perf-bench: the fold checkpoints land in the tool's shadow, not the state copy it benches
status: candidate
where: tools/perf-bench.py (`install_guards`); tests in `tests/test_perf_bench.py` (CheckpointShadow, Recorders)
added: 2026-09-18
pr:
tier: fix
offered:
closed:
---
Upstream ships both tools/perf-bench.py (their PR #1057) and the fold checkpoints, so its bench has the same open door: the event model writes one checkpoint document per folded JSONL file at run time, with Path.write_text and os.replace, into the directory kernel/judge.py's provider names, and none of the tool's shadows covers it. A bounded smoke run against a 39-session copy left 91 new files (716 KB) under the copy's checkpoints directory, reported by the census as new, and a second run restored from them, so its cold rows were warm. The fix is one guard in install_guards: em.set_checkpoint_dir with a provider naming the shadow's checkpoints directory, recorded as a diverted path and listed in the neutralized set; an event model with the directory provider but no setter is an error, one without checkpoints is skipped. Tests: CheckpointShadow drives the real event model's write door in-process and asserts the copy's tree hash unchanged and the document in the shadow (red before the fix); the Recorders cases and the end-to-end pins carry the new name. Filed 2026-09-18 by the fork's performance session; the offer waits on the no-new-upstreaming hold.
