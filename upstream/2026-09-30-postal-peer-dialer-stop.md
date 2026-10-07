---
title: The postal peer-identity, peer-tier, read-receipt, quarantine, peers and token tests stop the peer dialers their up notifies start
status: candidate
where: tests/test_postal_peer_identity.py (_end_dialer, new; its registration after each up notify); tests/test_postal_peer_tier.py (the same); tests/test_postal_read_receipts.py (the same); tests/test_postal_quarantine.py (the same); tests/test_postal_peers.py (the same, after PeerMode's three up notifies); tests/test_postal_token.py (the same, after PeerTokenPlumbing's up notify); upstream/2026-09-30-postal-peer-dialer-stop.md (this entry)
added: 2026-09-30
pr: 939
tier: docs
offered:
closed:
---
Each up notify a test sends through peer_update starts a _peer_loop dialer thread, and no test in these six modules ended one. In the identity, tier, read-receipt and quarantine modules the dialers outlive their tests: at their modules' ends the identity module leaves 2 running, the tier module 6, the read-receipt module 3 and the quarantine module 6. A dialer whose row a later setUp cleared exits at its next backoff wake; one whose row outlives the module redials a loopback port nothing listens on, backing off to 30 s, for the rest of the process. In the peers and token modules the test or its tearDown removes the row, so each dialer (PeerMode's three, PeerTokenPlumbing's one) exits at its next backoff wake, about 2 s after its test, while the next tests run. On the fork the leaked dialers made tests/test_thread_stop_census.py's ParseCacheRetention pin fail intermittently on the free-threaded build: a dialer's exchange replaced a module-level value that another thread had made, and the pin's process-wide gc.collect() counted the dropped objects. The project has no such pin, so there the defect is the leaked threads alone. The fix is tests only: each up notify is followed by addCleanup(_end_dialer, host), which sends the kernel's down notify while the row is still there, sets the dialer's wake on each 20 ms poll (the loop clears its wake after each exchange, so a single notify can be lost) and fails if the thread is still alive 10 s later. Tests only, so docs tier.

The project's copies of the identity, tier, read-receipt and quarantine modules match the fork's (the project's main as of 2026-09-30). Its copies of the peers and token modules differ from the fork's only away from the changed lines (a fork-side cleanup in RecallAfterTheCarry; a comment and two blank lines in TrackedIsABoolean) and carry the same four up notifies.

An offer to the project makes three edits to each module's _end_dialer:
- Drop write=False from the helper's down notify. The project's peer_update takes no such argument (its signature there is peer_update(data)), and it writes no mirror file, so a plain down notify is the equivalent.
- Drop the docstring's clause that explains write=False.
- Drop the docstring's reference to tests/test_thread_stop_census.py, a module the project does not carry.
