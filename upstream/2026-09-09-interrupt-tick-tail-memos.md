---
title: Awaiting overlay: the states log is folded append-incrementally instead of re-walked per _session_awaiting call, and the interrupt tick's two memos (intrMarks, statesOverlay) report under GET /perf
status: merged
where: kernel/kernel.py (_states_awaiting_overlay, _states_overlay_step, _intr_marks_memo_report, the tick tail), kernel/event_model.py (fold_records on=, _read_jsonl_incremental on_fail=), docs/reference.md, tests/test_states_overlay_fold.py and three sibling modules
added: 2026-09-09
pr:
tier: fix
offered: their PR #1228
closed: 2026-09-10
---
Perf audit row 23. The C3 slice of the perf4-readers entry (the states-overlay fold) and the _intr_marks_memo_report of the tick-jobs entry are offered here as one PR; the two parent entries note it. Filed directly from the upstream base.
