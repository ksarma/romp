---
title: Names registry: the kernel's writers leave a record that reads with no name alone, and bin/romp publishes the record atomically
status: offered
where: upstream branch names-empty-record-offer, re-derived from fork PR #246 (commit 6791ef4f): `kernel/kernel.py` `_names_fields_for_edit`, `_NAMES_REREAD_S`, `_names_problem`, `_names_refusal` and the three writers; `bin/romp` `_romp_record` (temp file plus mv); tests `tests/test_kernel_session_color.py`, `tests/test_kernel_names.py`, `tests/test_color_route.py`, `tests/romp.bats` (a race leg)
added: 2026-09-09
pr:
tier: fix
offered: their PR #1215
closed:
---
Audit row 17's remainder after their #1138 and #1066: a rename, recolor or palette switch published a record with empty fields over a record that read as 0 bytes (the tmux rename hook's truncate-then-write window, or a damaged file), erasing cwd and colours while reporting success. The writers now re-read once after a short pause and refuse a record that still reads with no name; bin/romp writes a temp file and renames. _NAMES_LOCK stays a separate candidate.
