---
title: Perf B6: the postal MCP server resolves the session list once per heartbeat and once per tool call (`_self_identity`), the bus answers a beat with `{ok, local}`, a peer-mode session stops beating once the bus confirms it local, and the bus advances its idle count on an unanswered kernel listing only when it has evidence that sessions existed
status: candidate
where: fork PR #234 (`perf-b6`, merged 2026-09-06): `postal/postal_service.py`; tests `tests/test_postal_heartbeat_fetches.py` (new), `tests/test_postal_delivery.py`, `tests/test_postal_bus_lifetime.py` (the idle gate and monitor tick), `tests/test_postal_live_only.py`, `tests/romp-postal.bats` (the heartbeat route against a private bus), identity-stub updates in six other postal tests
added: 2026-09-07
pr: 234
tier: fix
offered:
closed:
---
Upstream's postal server beats the bus every 30 s per session, and each beat resolves the session list through the kernel's `GET /sessions` three times (twice in the MCP, once in the bus): with about 30 sessions that is three requests per second at 200 ms each on a kernel whose pusher already saturates a core, and it was the whole of the `/sessions` traffic the live counters showed (92 requests per 30 s). In the legacy singleton mode the loop keeps beating, because there the bus can be switched to client-only under running sessions and heartbeats are its only presence mechanism. With the idle-gate change a kernel blink no longer stops the bus under live sessions, while a bus that never saw sessions keeps its autostop (the evidence is primed from the presence twin on a fresh bus). Also on the PR: the orphan sweep, recall and sent receipts fetch one listing per operation instead of one per mailbox, and the remote-sids mirror is rewritten each monitor poll so expired remote beats leave it within a tick. Measured: fetches per beat 3 to 2 on the first beat, then 0 for a peer-mode local session; per tool call 3 to 2, then 1 once confirmed local; the orphan sweep 28 to 1 per poll.

No `/perf` dependency. Port note: the fork's `postal_service.py` has diverged from upstream's (user todos; recipient resolution and recall include comment-thread rows, which this PR also touched), so the offer re-derives the heartbeat, idle-gate and one-listing changes over upstream's file and leaves out the thread-row hunks unless the file comments work has landed there.
