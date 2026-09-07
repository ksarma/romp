---
title: The kernel's WebSocket receiver drops fragmented client messages — any large browser→kernel send silently evaporates
status: resolved-upstream
where: `wsfrag` branch PR
added: 2026-08-10
pr:
tier:
offered: their PR #332
closed:
---
Upstream fixed this themselves in v0.7.0 (`afc30e35`, same week we did): FIN-aware reassembly as `_ws_recv` per-frame + `_ws_recv_message`, message cap, ping-between-fragments answered. The fork's v0.7.0 merge adopted their two-function shape and grafted in the two pieces theirs lacks, which are the RESIDUAL candidate: EOF-mid-frame returns a clean close instead of crashing the reader thread with a struct.error on a truncated length-extension/payload, and the big-int XOR unmask replaces a per-byte Python loop that blocks the reader thread for seconds on a multi-MB attachment frame. Both live in the fork's `_ws_recv`; tests/test_ws_fragmented_frames.py pins them (their tests/test_ws_fragmentation.py covers the rest). Small, clean offer.

Status detail (migrated from the table): resolved upstream; **residual MERGED — upstream PR #332**
