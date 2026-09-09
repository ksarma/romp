---
title: Chat: a send's queued copy carries the id the press minted, so its cancel removes exactly that copy
status: offered
where: upstream branch press-qid-offer, re-derived onto upstream's kernel-minted qid from fork PR #385 (queuejoin) and the fold decisions: `ui/webview/send-pending.ts` and `render.ts` (mintQid at the press, the id on the sendMessage frame and the cancel), `kernel/kernel.py` (the parked op's fourth slot, _client_qid and _wire_qid, the signature-gated handover to backends that identify copies), `kernel/sdk_backend.py` (unqueue by id, no text fallback), `docs/read-side.md`; tests `tests/test_queued_copy_press_id.py` (new), `tests/test_queued_copy_identity.py`, `tests/test_kernel_send_park.py`, the served `tests/test_queued_copy_held.py`, and the webview send-pending suites
added: 2026-09-09
pr:
tier: fix
offered: their PR #1224
closed:
---
Audit row 3, the sendId mechanism expressed on upstream's qid: a parked send carried no id until the drain, the client latched an id from the first same-text copy, and no cancel named an id, so two same-text copies could leave a phantom bubble or cancel the wrong one. The kernel mints an id for every copy it queues; a client that pressed supplies its own from the press. Filed against main with the id at parked-op index 3 (whichever of #994 and this lands second pads the layout). The feeder hold (queued-sends-not-fused) stays a separate candidate.
