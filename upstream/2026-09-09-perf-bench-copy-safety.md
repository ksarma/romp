---
title: `tools/perf-bench.py`: a state copy is only read (every kernel write into it, the import-time repo-root marker included, lands in a shadow and the census prints on every exit path), the no-transcript error waits for the 365-day backfill and names its counts, and `--cwd-map FROM=TO` resolves a copy whose registry cwds a redaction rewrote
status: offered
where: fork PR #428 (`perf-bench-copy-safety`): `tools/perf-bench.py`, `tests/test_perf_bench.py`
added: 2026-09-09
pr: 428
tier: fix
offered: their PR #1057 (rides the dev-bench offer as commit `5ad86def` on the maintainer review commit `75127a4f`; the PR body gained an Added-after-review section)
closed:
---
Follows the `perf-bench-tool` entry: the tool is not on upstream main but ships in the open offer romp-on/romp#1057 (branch `dev-bench-offer`), so once that bundle merges upstream carries the tool without this change unless the offer branch takes it first. A run against a redacted, mirrored copy on another machine (2026-09-09) found the kernel writing `repo-root` at import and `session-order.json` and `order-audit.jsonl` from the push path into the copy while the census reported zero writes (the diff ran on the success path only), the no-transcript error raised before the backfill so a copy older than the 48 h discovery window tripped it, and registry cwds rewritten by the redaction while the projects/ directory names kept the original left discovery with nothing. The change is self-contained in the tool and its test module and applies to the offer branch as it stands.
