---
title: The ws liveness dispatch-return test waits for the second ping to leave before it clears, and the judge's read order is pinned
status: candidate
where: tests/test_ws_liveness.py, class PhantomPanesAreDropped: test_c3_a_peer_is_never_judged_while_its_handler_is_inside_a_dispatch (the fix), test_c3c_a_ping_that_leaves_after_the_clear_is_a_new_outstanding_ping_stamped_as_it_left (the late order run on purpose), test_c3d_a_handler_returning_from_a_dispatch_between_the_judge_two_reads_is_not_dropped (the pin of the judge's read order), test_c3e_a_handler_entering_a_dispatch_between_the_judge_two_reads_is_not_dropped (the pin's other boundary), and the module-level _StampClearForcing and _SplitReadClient instruments; this entry: upstream/2026-09-20-ws-liveness-order.md
added: 2026-09-20
pr:
tier: docs
offered:
closed:
---
Upstream's copy of tests/test_ws_liveness.py carries the same harness race: test_c3 clears pingAt (its stand-in for the handler's return from a dispatch) and asserts None at once, while the second beat's ping, queued two lines earlier, may still be on its way to the socket, where the sender stamps pingAt with the clock. Both orders are valid kernel states, so the kernel is unchanged: the test now waits for that ping to reach the peer before it clears, the late order is run on purpose by its own case, and the judge's read order (inRead before pingAt in _keepalive_all), which nothing pinned, is pinned by a case that reds when the reads are swapped, since the swap drops a live peer. Tests only.

## Origin

Found by the CPython 3.14t (free-threaded) CI cell on fork PR 864 (heldmail-readers), whose diff touched nothing on the path: every function on the path (_ws_sender, _note_ws_inbound, _keepalive_all, _new_ws_client, _ws_send, _client_send, _dist_ver, the handler loop) and the test module are byte-identical between that PR's merge-base and its head, and the test module is byte-identical again at 5b8df8f5c, this change's base. One red in that cell (`AssertionError: 1800000090.0 is not None` at tests/test_ws_liveness.py:212; the other 17227 tests passed); unforced, 320 of 320 green on 3.14t on the 60-core box that diagnosed it (10 and then 100 runs at each of the two trees, 100 more at the merge-base pinned to two cores) and 10 of 10 on 3.12. Proved latent at the merge-base by forcing the order: under the late forcing the unfixed test reds at that PR's merge-base (3.14t and 3.12), at its head (3.14t) and at 5b8df8f5c (both interpreters).

## Mechanism (file:line at 5b8df8f5c)

Two writers of client["pingAt"], each atomic under the client's qlock, race in ORDER:

- The clear. `_note_ws_inbound` (kernel/kernel.py:53837; the write at 53843 under the qlock) sets pingAt to None: the peer spoke, no ping is outstanding. In the kernel it runs on the handler thread, on a pong or a message (77668, 77671) and in the `finally` of a dispatch (77688 to 77689), after which the loop top sets inRead = True (77665). In the test the main thread calls it at line 211, standing in for the return from a dispatch.
- The stamp. `_ws_sender` (53700), the client's ws-send thread, when a ping frame reaches the socket (53715 to 53718): under the qlock, if pingAt is None, pingAt = _ws_clock(). The liveness clock starts when the ping reaches the socket, not when the beat queued it. The test's clock at that beat is 1800000090.0.

Line 209 (`_keepalive_all(now=t0 + 3 * WS_DEAD_S)`) queues the second beat's ping; line 211 clears; line 212 asserts None. Line 207 waited for the first ping to leave; nothing waited for the second. The stamp before 211 is a no-op (pingAt was t0, not None); after 212 the test passes; between 211 and 212 it reds with CI's exact value. Two facts at two moments: "no ping is outstanding" (the clear, at 211) and "the second ping has left" (the stamp, whenever the sender reaches the socket). The kernel is consistent under both orders: a ping that leaves after the clear is a new outstanding ping, stamped at its leave time and judged on a window from there, so production never drops a live peer from this. Only the test asserted one order.

The window in microseconds, traced unforced on the unfixed test (every traced run green): in the diagnosis (30 runs, 3.14t) the stamp landed 68 to 158 us after the clear while the main thread was past line 212 within 23 to 51 us of it; re-traced for this change, 10 runs per interpreter, the stamp landed 127.2 to 170.9 us (3.12) and 80.3 to 196.1 us (3.14t) after the clear while the main thread was past the assertion within 1.8 to 3.5 us (3.12) and 3.2 to 4.5 us (3.14t). The re-trace's marker is the entry of the third `_keepalive_all` call, the first statement after the assertion; the diagnosis does not state its marker, the likely reason the second figures differ; both traces put the stamp roughly 100 us behind the main thread. The red needs one preemption of the main thread in that gap. The GIL hides it: after the enqueue at 209 the main thread runs bytecode to 212 with no blocking call, and the woken sender gets the GIL only on a switch-interval drop request or a blocking call by the holder, neither of which happens in the gap. The interleaving is legal under the GIL all the same, and the same forcing reds 3.12. A two-vCPU hosted runner with four competing threads (main, sender, handler, peer) produced it once; a 60-core box did not in 320 runs.

## The fix, and the forcing in both directions (the reviewer's condition one)

test_c3 now waits for the second beat's ping to reach the peer, `self.assertTrue(self._settle(lambda: len(peer.pings) == 2), ...)` (line 366), before it clears (367) and asserts None (368), the way test_b already waited; every other assertion is unchanged. The harness is keyed on the event it assumed (the ping left) instead of on the scheduler.

The forcing is `_StampClearForcing` (tests/test_ws_liveness.py:93 to 183), a test-local instrument over the two module functions the harness threads look up by name, so the real sender runs: a queue proxy holds the second ping before its stamp, a socket-lock proxy marks the stamp point (the sender takes that lock right after the stamp), and the wrapped `_note_ws_inbound` is the clear. `late` holds the stamp until the clear has landed and lets the clear return only once the stamp point has passed; `early` is the converse, the clear waits for the stamp point first. Every wait is bounded (1.0 s) and `holds` records whether the event or the bound released it; `forced` is True only when every hold was released by its event. Runs: five pytest processes per cell, the forcing applied by a plugin that takes the instrument from the committed module's source, env stripped of every ROMP_* variable and CLAUDE_CODE_SESSION_ID, `-p no:cacheprovider`, XDG_STATE_HOME under a scratch with session-hosts off, `sys._is_gil_enabled()` recorded from inside pytest (False on every 3.14t run; 3.14.6 free-threading here, 3.14.7 in CI), CPython 3.12.3 the other interpreter.

- Unfixed test_c3, from a git archive of 5b8df8f5c. Late: 0 of 5 pass on 3.12 and 0 of 5 on 3.14t, every run `AssertionError: 1800000090.0 is not None` at line 212, CI's text, the forcing satisfied (both holds released by their events). Early: 5 of 5 pass on each interpreter.
- Fixed test_c3. Early: 5 of 5 pass on 3.12 and 5 of 5 on 3.14t, the forcing satisfied. Late: 5 of 5 pass on 3.12 and 5 of 5 on 3.14t; in all 10 runs the hold on the stamp expired at its bound unreleased, because the fixed test clears only after the second ping has reached the peer, which is after its stamp: the late order is unreachable from the fixed test, not tolerated by it. The failure mode the condition guards against, a fix that swaps which order the test asserts, would red under the early forcing; this fix passes both.
- Unforced, the whole module: 14 of 14 in five runs per interpreter at the fixed tree, and 14 of 14 on 3.14t at the committed head.

## The late order, run on purpose

test_c3c (line 389) runs the late order through the same instrument and asserts `forcing.forced`, so a pass never comes from the scheduler happening to order the writes: the late ping is stamped at its leave time (pingAt == 1800000090.0 right after the clear) and the peer is judged on a window from there (alive at WS_DEAD_S - 1 later, dropped at WS_DEAD_S). Mutation proof, since the semantics it pins hold at the base: the kernel one-hold the reviewer ruled out, emulated in a scratch copy of kernel/kernel.py (`_note_ws_inbound` sets a flag on the client under its qlock after the clear; `_ws_sender` skips one ping stamp while the flag is set): test_c3c red 3 of 3 on 3.12 and 3 of 3 on 3.14t, `AssertionError: None != 1800000090.0 : the late ping is a new outstanding ping, stamped as it left`; fixed test_c3 red too, at its wait for the third ping's stamp (line 370), since its third beat uses the same clock value as the clear; the other 12 tests green.

## The pin of the judge's read order (the reviewer's condition two)

`_keepalive_all` (54239) reads inRead (54254) before pingAt (54258). The comment at 54254 to 54257 says why: the handler ends a dispatch by clearing pingAt (77689) and THEN setting inRead (77665), so a beat between those two writes, read the other way round, pairs a stale ping with a fresh read state and drops a live peer (a 2026-09-04 review find). Until this change nothing pinned that order, so a future reader tidying two adjacent reads into a different order would reintroduce a dropped peer with every test green. The diagnosis forced the pair both ways: the shipped order drops no live peer 3 of 3 under 3.14t and 3.12; a control with the reads swapped drops a live peer 3 of 3 under both.

test_c3d (line 420) is that control made permanent. It runs the real `_keepalive_all` on its own thread and lands the handler's two writes, in the handler's order (the pingAt clear, then inRead = True), between its two reads through `_SplitReadClient` (186 to 205), a dict subclass with a door after whichever of the two reads comes first on the judge's thread, so the door sits in the same place in a swapped copy; every other read, and every read on another thread, is a plain dict read. Mutation proof: in a scratch copy of kernel/kernel.py, `pa = c.get("pingAt")` moved above `in_read = c.get("inRead", True)`: test_c3d red 3 of 3 on 3.12 and 3 of 3 on 3.14t, `AssertionError: False is not true : a live peer whose handler returned to its read as the beat judged it is not dropped`, with the kernel's own line `ws: dropping timeline client ... no pong for 90s (last heard 0s ago)` in the log; the other 13 tests green in the swapped copy. As shipped the module is green 5 of 5 on each interpreter. test_c3e (line 448) is the other boundary, a handler entering a dispatch (the clear, then inRead = False) between the reads: both read orders keep that peer, a stale ping read first being excused by the fresh inRead = False, so it holds the no-drop claim for the entering boundary while test_c3d carries the order; no forcing or simple mutation reds it, by construction, and its docstring says so.

## Why the kernel is unchanged

Suppressing the late stamp would leave a ping on the wire never judged, so the obvious kernel fix introduces a real defect where the test fix introduces none. kernel/kernel.py is untouched; the one-hold appears only as an emulated mutation in a scratch copy, the proof that test_c3c would catch it.

## Also in the change

The module mints its own state root at import and now writes `off` into `<root>/romp/session-hosts` (line 31), the suite's rule for a test that mints a state root; the module never connects a session, so the line changes no behaviour. The state-isolation order scan (tests/test_state_isolation_order.py) passes over the changed module.

## Upstream

The test module is byte-identical between 5b8df8f5c and the project's tip as last fetched (55d8e8f0c, 2026-09-20), and the project's `_ws_sender` stamp and `_keepalive_all` read order are the same code (its differences in those two functions are a perf counter, a `pv` field in the beat and a reveal-copy retire, none on the path), so the fix and the pins apply there as they stand.

## Tier

docs (tier 0): tests only, no product code. Upstream's tier check treats docs as merge on green for every author.

2026-09-20: built on the fork branch ws-liveness-order from 5b8df8f5c, one tests commit; `pr:` blank until the fork PR exists. Not offered; the offer is the user's per-change call.
