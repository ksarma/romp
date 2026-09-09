---
title: Spend: the connect-time scan for the last cost-state record reads a long transcript line in linear time
status: offered
where: upstream branch spend-scan-linear-offer (a follow-up to their merged #1200, from the review record posted on it): `kernel/sdk_backend.py` `last_cost_state` (fragment list joined once per line, `max_line` cap of 4 MB, two docstring corrections); tests `tests/test_sdk_backend.py` `SpendRecord` (join order, exact-cap boundary, the scan_bytes bound and floor, the copy and memory bound without timing assertions)
added: 2026-09-09
pr:
tier: fix
offered: their PR #1207
closed:
---
The backward reader in their #1200 concatenated the carried fragment on every 64 KB step, quadratic in the length of a transcript line within the 8 MB bound (a 7 MB line: about a hundred growing copies, 21 MB peak). The reader now keeps the pieces in a list and joins once at the newline; a line longer than 4 MB is skipped as not a record, bounding memory by the cap. Range read, scan_bytes and floor unchanged. No fork counterpart: the change is written on the merged code.
