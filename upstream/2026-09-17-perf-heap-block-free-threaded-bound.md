---
title: The heap block's 5 ms read bound is the GIL build's; a free-threaded build reads ten times that
status: candidate
where: tests/test_perf_heap_block.py Overhead.test_the_read_stays_under_five_milliseconds_over_populated_caches
added: 2026-09-17
pr:
tier: docs
offered:
closed:
---
Upstream's test (romp-on/romp pull 1763) pins the /perf heap block's read to a median under 5 ms over populated caches, thirty times a fresh lab process's 166 us, and never ran on a free-threaded build: upstream's CI has Python 3.10 to 3.13 cells only. The fork's CI adds a 3.14t cell (PYTHON_GIL=0) run as one serial pytest process, and there the case read a median of 5.451 ms (min 5.242, max 6.303) after about 10,000 tests while the module alone reads 120 us on the same interpreter: a tight floor, not jitter or load. The cost is sys.getallocatedblocks(): on a free-threaded build (CPython 3.14, Objects/obmalloc.c) it walks every thread state's mimalloc heaps and then the abandoned pool once per heap tag, so it costs the process's thread history and never falls back when objects are freed (measured on 3.14.6t: 1.5 ms after 500 exited threads, 2.5 ms after 2,000; 1.1 ms at this module's place in the suite's alphabetical prefix with 8 live threads), where the GIL builds' pymalloc walks live pools only. Every other gauge in the block costs 0.1 to 1.5 us on both builds and the block without that read 7 to 8 us. The fork's change is test-side and the kernel is untouched: the bound is gated on the BUILD (FREE_THREADED_BUILD, 't' in sys.abiflags, the kernel's own idiom; READ_BOUND_S is 50 ms there and upstream's 5 ms on every GIL build), the bare walk is timed beside the read and printed in the case's line and its failure message so a red on either build names its cause from the CI log, the test's name stays and nothing retires. Any free-threaded runner of upstream's suite meets the same floor, so the gate and its header are the offer. Filed by the 2026-09-17 catch-up fold (fixer round c4, ruling 8 and the round's late steer); the offer waits on the no-new-upstreaming hold like the 2026-09-16 entries, the ledger being the queue.
