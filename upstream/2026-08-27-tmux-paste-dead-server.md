---
title: The tmux paste sequence reports success on a dead server: `_Tmux._run`/`_fire` swallow every subprocess error and ignore nonzero exits, so when the tmux server or session dies AFTER the clear-guard passes, set-buffer / paste-buffer / the submitting Enter all silently no-op and the message vanishes with no trace — their #741 clear-guard refusal covers only the pre-clear death (empty capture → no box region), and the never-delivered settle catches the loss only when a LATER send happens to overtake the echo
status: merged
where: fold-hardening fix in `upfold0827b` (`b8aef6ba`): checked variants (`set_buffer_checked`/`paste_buffer_checked`/`send_keys_checked`) read the returncode, used only inside `paste()`; any failure aborts the paste with a loud stderr line naming the failed step (returncode contract verified empirically on tmux 3.4: dead server / missing session / missing buffer all exit 1, success 0; set-buffer does not auto-start a server); pinned in `tests/test_user_todos.py` (dead-server-at-set-buffer / at-paste-buffer / failed-Enter tests)
added: 2026-08-27
pr:
tier:
offered: their PR #876
closed: 2026-09-02
---
MERGED as-is (head is an ancestor). Branch retired. OFFERED 2026-09-02 (branch `tmux-paste-checked`, `30825998` off tip `70a36077`): only the three checked TmuxBackend methods + the paste/Enter checks + the pane-clear fake adaptation; fork refusal hooks/marks/nonces excluded; red-first 8/9 new tests fail on base; full suite 6502 green (xdist); review clean, scaffold CI green (since-closed fork #151). Upstream ships the same swallowing primitives and the same unchecked paste sequence verbatim (their #741). An offer carries ONLY the checked variants + paste() wiring + the loud abort — the fork's refusal hook, pending-paste marks, nonces and user-todo stand-down machinery are fork-only and must not ride. The offer's failure behavior matches their own clear-guard refusal idiom (stderr, no paste); tests would re-home off test_user_todos.py onto a plain paste-path suite.

Status detail (migrated from the table): ✅ **merged** — their PR #876, merged as-is 2026-09-02 — ✅ came home in upfold0905 (2026-09-05)
