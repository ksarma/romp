---
title: One encode per payload per build on the pusher thread (PLAN-2 P5 + P8): the feed and bars dedup signatures are tuples of the per-entry strings the delta paths already make (`_feed_sig`, `_bars_sig`) instead of a sort_keys re-dump of the stripped payload; the whole frame is a `_LazyWire` cell serialized on the first send that needs one (a fresh socket, a re-base, a client without deltas, a delta past the size guard) and kept in the wire tuple, so a rebuild whose clients all hold a base never serializes the frame; `_feed_parts` memoizes the per-card encode on the build's asks list (a ledgers-only refill encodes no card); `_delta_split` parses a collection's kind once; an unkeyable bars build keeps the whole dump and `_dedup_sig`. The wire section of `_push` and `_pusher_cycle_jobs` now catch: a raise there (HEAD had one waiting, a card without an `itemId`) killed the pusher thread for the process's life. `/perf memos.wire` reports the memo's hits, the whole frames made and the fallback
status: candidate
where: fork branch `perf2-serialize` (kernel/kernel.py `_LazyWire` / `_wire_text` / `_wire_len` / `_feed_sig` / `_feed_est` / `_bars_sig` / `_bars_est` / `_delta_keyer` / `_feed_parts` / `_send_client` / `_send_slot*` / `_send_feed_now` / the `_push` wire section; tests/test_wire_once_per_build.py, tests/test_feed_delta.py, tests/test_view_deltas.py, tests/test_kernel_pusher_snapshot.py, tests/test_perf_stats.py)
added: 2026-09-06
pr:
tier:
offered:
closed:
---
Pure kernel change, no fork-specific content; the wire shapes are unchanged (the same tuple positions, `w[3]` a cell with `.text()`), every whole frame is still the tinted legacy body (no trgb-free cap body: dropped per the P8 review), and `_dedup_sig` stays the sig=None fallback. The one behaviour change is towards more sends, never fewer: the tuple is key-order-sensitive where the sort_keys dump was not (an equal-content reorder re-sends once, then dedups). The size guard reads the entries' byte total until the frame is made (a percent or two under for the bars). Measured offline with tools/perf-bench.py before/after on the same state copy (2026-09-06); the live saving is per rebuild, about 0.3 s of a 1.6 s rebuild cycle in the kernel4 profile, shrinking as rebuilds get rarer (PLAN-2 P10-P12)

Status detail (migrated from the table): **candidate**
