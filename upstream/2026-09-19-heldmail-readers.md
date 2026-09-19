---
title: Readers that cannot parse skip the row and say so: the notices rev, the quarantine directory, the light-theme held-mail border
status: candidate
where: kernel/kernel.py (_notice_row_bad_field, _notice_parse_rows, _notice_rows, _notice_rows_unlocked: upstream, the notices reader; _held_records, _corrupt_aside_name, _say_hold_unreadable_once, _note_hold_dir_fault, _quarantine_cards and its build_feed and clearAll call sites: fork-only, the quarantine road F1 F3 F4 F5), ui/webview/feed.css (.fdismiss.fq-ok border: upstream), ui/webview/button-vocab.test.ts (the fq-ok case: upstream), ui/webview/feed.ts (clearable comment: fork-only), tests/test_held_mail_readers.py (NoticeRowTypeFault: upstream; ClearAllLeavesHolds and HeldMailReader: fork-only), tests/test_kernel_trust.py (QuarantineCards: fork-only)
added: 2026-09-19
pr:
tier: fix
offered:
closed:
---
One rule at every site: a reader that cannot parse a row must not report the store absent and must not take down callers that had nothing to do with the bad row; it skips the row, names the session and the key in the log, and keeps the board. Upstream-facing part: one type-wrong rev, t or expiresAt in one row of one session's notices/<sid>.jsonl raised ValueError out of every feed build (the push cycle and GET /feed.json alike); the shared parse now skips that row and says it once per episode, naming the session, key, field and type, never the text. Also upstream: the held-mail Approve button's border reads the accent token through color-mix instead of a dark-accent literal, so the light theme's text and edge share a hue. Fork-only (upstream deleted the quarantine cards; the fork keeps them): a hold's card stands through Clear-all because the reader takes no cleared ledger, and the directory reader is the bus's _list_json_records shape ported (a record it cannot read moves aside once and is said; a directory it cannot list is said once per episode; the board is kept).
