---
title: The postal peer-identity, peer-tier, read-receipt and quarantine tests stop the peer dialers their up notifies start
status: candidate
where: tests/test_postal_peer_identity.py (_end_dialer, new; its registration after each up notify); tests/test_postal_peer_tier.py (the same); tests/test_postal_read_receipts.py (the same); tests/test_postal_quarantine.py (the same); upstream/2026-09-30-postal-peer-dialer-stop.md (this entry)
added: 2026-09-30
pr:
tier: docs
offered:
closed:
---
The project's copies of the four modules match the fork's (the project's main as of 2026-09-29) and leave the same threads running: each up notify through peer_update starts a _peer_loop dialer that no test ends (at their modules' ends the identity module leaves 2 running, the tier module 6, the read-receipt module 3 and the quarantine module 6). A dialer whose row a later setUp cleared exits at its next backoff wake; one whose row outlives the module redials a loopback port nothing listens on, backing off to 30 s, for the rest of the process. On the fork this made tests/test_thread_stop_census.py's ParseCacheRetention pin fail intermittently on the free-threaded build: a dialer's exchange replaced a module-level value that another thread had made, and the pin's process-wide gc.collect() counted the dropped objects. The project has no such pin, so there the defect is the leaked threads alone. The fix is tests only: each up notify is followed by addCleanup(_end_dialer, host), which sends the kernel's down notify, sets the dialer's wake on each 20 ms poll (the loop clears its wake after each exchange, so a single notify can be lost) and fails if the thread is still alive 10 s later. An offer drops the helper docstring's reference to the fork-only census module. Tests only, so docs tier.
