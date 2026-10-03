---
title: test_ws_liveness's c3 waits for its second ping to reach the peer before it clears the liveness clock, and a new test runs c3 with that window held open
status: candidate
where: tests/test_ws_liveness.py (PhantomPanesAreDropped.test_c3_a_peer_is_never_judged_while_its_handler_is_inside_a_dispatch: the settle on the peer's second ping before _note_ws_inbound; PhantomPanesAreDropped.test_c3_widened_c3_holds_when_its_second_ping_leaves_late, new); upstream/2026-10-03-tests-ws-liveness-c3-ping-race.md (this entry)
added: 2026-10-03
pr:
tier: docs
offered:
closed:
---
c3 could fail when the client's sender thread reached its second ping after c3 had cleared the liveness clock. The sender stamps pingAt as a ping goes out whenever pingAt is None, and c3 cleared it (_note_ws_inbound) right after the second beat, so a sender that reached that ping late stamped the beat's time and c3's assertIsNone read the stamp. On the fork this showed as a rare failure on the free-threaded 3.14t cell. c3 now waits until the peer has received the second ping before it clears the clock. A new test runs c3 with each text frame delayed 10 ms and the clear held for 50 ms: without the wait c3 fails at its pingAt assert in 100 of 100 runs on 3.14t and on 3.13, and with it c3 passes 100 of 100 on each. Tests only, so docs tier.

The race is latent in the project's public tree (upstream/main, last updated 2026-09-24): its tests/test_ws_liveness.py is byte-identical to the fork's before this change, and its kernel stamps and clears pingAt the same way. Its CI runs Python 3.10 to 3.13, all with the GIL, and has no free-threaded cell. Its _ws_send takes a fourth argument (deflate); the new test's wrappers pass every argument through, so the test needs no change for it (not run against that tree).
