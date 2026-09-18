---
title: The judge child refuses the pass that follows a done line as busy: the gate read the pass thread's liveness, which outlives its done line on a free-threaded interpreter
status: approved
where: kernel/judge.py (serve: an inflight flag cleared in the emit that writes the done line, read under emit_lock; the header comment); tests/test_judge_serve.py::Roads::test_a_pass_sent_on_its_predecessors_done_line_is_never_refused_busy_while_that_thread_exits
added: 2026-09-17
pr:
tier: fix
offered:
closed:
---
Upstream's serve loop gates one-pass-at-a-time on running[0].is_alive(); a thread is alive through its teardown after its last statement, and with the GIL off that teardown (200 to 500 us measured on CPython 3.14.6t) outlives the done line by more than a request's round trip, so the request following a done reads busy and the kernel (pass_) kills the child as answering something other than its done. Upstream CI has no free-threaded cell; the fork's 3.14t cell caught it (three reds in tests/test_judge_serve.py). The fix keys the gate on the done line itself, cleared in the same critical section that writes it; the pin lingers a stubbed pass thread after its done line in process, so it fails on every interpreter against the old gate.

2026-09-18: approved for offer by the user (batch 1 of the 2026-09-18 plan).
