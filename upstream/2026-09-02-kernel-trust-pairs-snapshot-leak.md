---
title: `tests/test_kernel_trust.py::PairsSnapshot` leaks `km._remotes` across modules under pytest-xdist — three tests fail on a parallel run, pass serially and alone
status: merged
where: fork commit `dd0166e4` (fork-side fix, already on fork main)
added: 2026-09-02
pr:
tier:
offered: their PR #892
closed: 2026-09-03
---
MERGED as-is (head is an ancestor). Branch retired. OFFERED 2026-09-02 (branch `trust-xdist`, `dd1d8850` off tip `31d8731b`, test-only): review refuted two file-name claims in the body’s "Not in this PR" paragraph (one file only mentions `_remotes` inside an assertIn string; the other loads the kernel under a separate module name and restores the map) — replaced with two surveyed planters that do share the module; scaffold CI green (since-closed fork #169). Found 2026-09-02 while validating the fallback-sid offer with `pytest -n 8` at upstream tip `70a36077` (3 failed on run 1, 0 on run 2 — worker-assignment dependent). Pre-existing at upstream tip, not a fork regression; upstream CI runs serially so it never sees it. Test-only.

Status detail (migrated from the table): ✅ **merged** — their PR #892, merged as-is 2026-09-03 — ✅ came home in upfold0905 (2026-09-05)
