---
title: `SdkBackend.__init__` snapshots `regs = list_regs(...)`, then `_reseed_echoes(regs)` may REFEED a proven-lost human send into a reg's persisted queue via `write_reg` (`_mark_dropped_echoes`, refeed path), then `_boot_reconcile(regs)` walks the PRE-refeed snapshot — so a session whose state tail is not machine-active (no cut turn, no dead tasks, no dead ask) reads an empty `queued` off the stale dict and is not resumed that boot despite the send now sitting in its queue on disk; it delivers only at the next spawn or boot
status: merged
where: inherited from upstream `b878b1ad` and present in BOTH merge parents (`kernel/sdk_backend.py`: `__init__`'s regs snapshot, `_reseed_echoes`, `_boot_reconcile`'s `r.get("queue")`)
added: 2026-09-02
pr:
tier:
offered: their PR #878
closed: 2026-09-02
---
MERGED as-is. Branch retired. OFFERED 2026-09-02 as commit A of the combined boot-reconcile PR (branch `boot-reconcile`, `03ffc92b`); review clean, scaffold CI green (since-closed fork #155). Fix shape: re-read the reg inside the reconcile loop (`read_reg` per sid — the RMW arm already does) or re-list after the reseed. Test: an alive reg with a human echo absent from its queue and a `waiting` tail; assert the boot resumes it with the refed text queued.

Status detail (migrated from the table): ✅ **merged** — their PR #878 (commit A), merged as-is 2026-09-02 — ✅ came home in upfold0905 (2026-09-05)
