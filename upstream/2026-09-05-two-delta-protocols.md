---
title: Two WebSocket delta protocols coexist after upfold0905: the fork's feed deltas (a client announces `?caps=feedDelta`; `_send_feed` sends `{type:"feedDelta"}` frames behind the `READY_GATE_CAP` hold) and upstream's per-slot view deltas (`?delta=1&iid=…`; `_send_slot` / `_send_slot_delta` under the client's slot lock; `{type:"delta"}` frames; `needSlot`). The kernel-served shim announces both; the pusher sends the feed slot with the fork's protocol when the client announced `feedDelta`, else upstream's; timeline bars always take upstream's. At `ready`, `_send_feed_now` serves a `?delta=1` client that did not announce `feedDelta` (the Outline page) through `_send_slot`, so the served frame is the slot's base and the connect push that follows sends a delta rather than a second full frame; the feed's per-client state (`efeed`, the dedup slot, `dstate["feed"]`) is read and written under the client's slot lock on both paths, and `_client_reset_feed_base` is the one forgetter (round 2, 2026-09-05)
status: follow-up
where: `kernel/kernel.py` (the pusher's feed send site, `_shim`'s connect URL and reassembler, the WS `ready` handler); `ui/webview/*` (both receivers)
added: 2026-09-05
pr:
tier:
offered:
closed:
---
Convergence pending: one protocol should carry the feed. The fork's brings the ready-gate hold and the loud-drop accounting (`_note_ws_drop`, `_WS_DROPS`); upstream's brings the per-page instance id supersession and the slot lock. Decide which survives and port the other's properties onto it. The one full frame per `ready` for a `?delta=1`-only client holds while the connect push's delta stays under `_DELTA_MAX_FRACTION` of the full frame; a larger delta pops the slot's base and re-sends a keyed full frame (the size fallback, unchanged). Until then a client that announces neither gets whole frames, and nothing is lost.

Status detail (migrated from the table): follow-up
