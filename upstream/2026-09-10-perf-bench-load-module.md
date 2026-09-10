---
title: perf-bench: the kernel and its SDK backend load through load_source, so the tool runs clean under the load_module() deprecation
status: offered
where: kernel/loadsource.py tests/test_perf_bench.py tools/perf-bench.py
added: 2026-09-10
pr:
tier: fix
offered: their PR #1313
closed:
---
From the fold's slice 4g scout (romp-performance-1 item 12). The loader is bootstrapped from the tool's own checkout (kernel/kernel.py's four-line idiom), not from --repo, so a candidate checkout from before their #1278 stays benchable; the fork's own fix (loader from --repo, refusing checkouts without kernel/loadsource.py) has a different shape, so the next fold will see a conflict there.
