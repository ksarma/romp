---
title: Pusher: an exact chat-diff return, timing seams inside push.chat and push.send, and three memos.wire counters
status: candidate
where: kernel/kernel.py (`_chat_diff`, `_PerfStats.STAGES` and `CONTAINERS`, `_push`, `_delta_split`, `_send_slot_delta`, `_wire_stats`, `_ua_kind`, `_ws_sender`, `_PerfStats.client_send`); docs/reference.md; tests in `tests/test_kernel_delta_send.py`, `tests/test_first_cycle_stage_split.py`, `tests/test_wire_once_per_build.py`, `tests/test_perf_stats.py`
added: 2026-09-18
pr: 759
tier: fix
offered:
closed:
---
Upstream ships the same pusher: _chat_diff walks every event of every served tab per cycle to return its length, because the non-connect push re-stores the cache hit's own events list as the baseline and the next diff receives one object on both sides; the exact return answers len(cur) when prev is cur, proved byte-identical on the wire by a test that runs six cycles over chat, feed and timeline clients twice, once with a verbatim copy of the old walk. The rest is measurement upstream lacks: push.chat and push.send become containers of six seams in stages_ms and the cycle split (sig / build / send, feedParts / barsSplit / compare), a container counting a nested container's rows through that container's own row so nested bytes are not double counted (a dotted stage under a plain job still counts directly), and memos.wire gains entries_walked, entries_encoded and feed_slot_split, which say what the keyed split walks and encodes per build and whether a feed client still takes the per-card slot path. Beside them, pusher.clients counts what each client's sender thread wrote to its socket, frames and bytes by the app the client declared and by a fixed browser kind classed from the dial's User-Agent header at the handshake (safari-ios, safari-mac, chrome, firefox, other, none; never the header itself), with the write's wall ms summed, counted and maxed per kind, the per-client numbers the phone work reads. Stage 1 of the fork's incremental-push design, the counters every later stage is judged on. Filed 2026-09-18 by the fork's performance session; the offer waits on the no-new-upstreaming hold.
