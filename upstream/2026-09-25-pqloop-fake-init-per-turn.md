---
title: PendingQueueLoop's fake client streams one init per turn, as the CLI does, so the mid-flight forwarding test no longer flakes; a pin forces the order that failed
status: candidate
where: tests/test_sdk_backend.py (PendingQueueLoop.setUp: GatedClient.receive_messages; PendingQueueLoop.test_second_turn_forwarded_immediately_when_the_first_is_sent_after_connect, new); upstream/2026-09-25-pqloop-fake-init-per-turn.md (this entry)
added: 2026-09-25
pr:
tier: docs
offered:
closed:
---
PendingQueueLoop.test_second_turn_forwarded_immediately_mid_flight is a flake at fork main under box load: 2 of 100 lone runs failed, and an in-process loop over its scenario held B in 231 of 15,600 iterations. Its fake client streamed a single init frame when the stream opened, where the CLI streams one init per turn once it reads the turn (_turn_frame's docstring in kernel/sdk_backend.py). The first send starts the session, and when the session thread handled that init before the test thread's enqueue of A, romp read the init as a turn the CLI had started on its own (_on_message raises inflight from 0), so A was fed mid-turn; its one-fed-text hold then waited for a take (a settle or a landed record), nothing streamed until the test released A, and B stayed in romp's queue past the test's wait. The fake now streams its init after it reads each turn, and a second test forces the failing order: A's enqueue waits until the receive loop has handled every frame the stream sends before a turn and waits on the client's turn queue. That test fails every time against the old fake, at the same assertion as the flake, and passes with the new one. Upstream's tests/test_sdk_backend.py carries the same fake line for line, and upstream's kernel has the same hold, the same inflight raise and the same _turn_frame, so its copy of the test is open to the same order (not measured there). Both tests need claude_agent_sdk importable (tests/test_host_transport.py adds the venv bin/romp-sdk-setup builds); CI installs none and skips them, so the flake shows in local runs only. Tests only; kernel/ is untouched.
