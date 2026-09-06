---
title: `list_regs`'s whole-listing last-good serve resurrects OTHER state roots' sessions, by two arms: (1) it misreads a MISSING `sdk/` dir as a transient scan fault — its own comment claims a missing dir "enumerates FINE", but `os.scandir` RAISES `FileNotFoundError` there, so a state root whose first write hasn't happened yet takes the fault arm; and (2) the fault arm itself serves the ENTIRE module-level `_REG_CACHE` (path-keyed, shared by every backend in the process), so any REAL enumeration fault on one root — PermissionError, EMFILE, transient I/O — serves rows cached from every other root too. Cross-root session resurrection in any process holding backends over several state roots — their own test suite's shape; found at the 2026-09-01 fold when a foreign echo reseeded into a fresh backend and the fork's todo-echo suite went red, only under full-suite ordering
status: merged
where: the fold merge (`upfold0901`), both arms: a `FileNotFoundError` arm ahead of the `OSError` arm in `kernel/sdk_backend.py` `list_regs` returns `[]` honestly (a dir that is gone took its regs with it — the listing contract's own unlink rule), and the surviving `OSError` arm's serve is ROOT-SCOPED — the cache filters to reg paths under THIS root's `sdk/` dir (reg paths are absolute, so the root is derivable), with a per-root incident sentinel; the last-good purpose stays for the faulting root's own rows. Pinned by `tests/test_sdk_live_rows.py` `test_a_missing_dir_is_empty_truth_never_another_roots_rows` + `FaultServeRootScope::test_a_fault_on_one_root_serves_only_that_roots_rows`
added: 2026-09-01
pr:
tier:
offered: their PR #874
closed: 2026-09-02
---
MERGED as-is (head is an ancestor). Branch retired. OFFERED 2026-09-02 (branch `listregs-roots`, `8a78d7a1` off tip `70a36077`): both arms; review clean, scaffold CI green (since-closed fork #149). Upstream ships the identical arm (their 2026-09-01 listing-completeness review round, `17f77df1`'s file), unfiltered serve included. Production mostly dodges it — one backend per process and `sdk/` exists once anything wrote — but a fresh install's first scan before the first write takes the fault arm too, and any future multi-root embedding inherits the resurrection. Small fix + two tests, cut clean off their tip; the offer carries BOTH arms (missing-dir honest `[]`, fault-arm root-scoped).

Status detail (migrated from the table): ✅ **merged** — their PR #874, merged as-is 2026-09-02 — ✅ came home in upfold0905 (2026-09-05)
