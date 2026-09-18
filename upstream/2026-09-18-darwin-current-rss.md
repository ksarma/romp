---
title: The kernel's rss_kb is the CURRENT resident size on macOS, with the peak as rss_peak_kb
status: candidate
where: kernel/kernel.py (_process_stats, _darwin_task_rss_bytes, _darwin_ps_rss_kb, _darwin_current_rss_kb), bin/romp (the perf memory line), docs/reference.md, tests/test_perf_stats.py (ProcessStatsFallback: the darwin-fallback cases), tests/romp-perf.bats (the macOS memory-line cases)
added: 2026-09-18
pr: 763
tier: fix
offered:
closed:
---
On macOS, which has no /proc, _process_stats reported ru_maxrss, the lifetime peak, under the same rss_kb name Linux uses for the current VmRSS, so a Mac's memory over uptime (the /perf process block, the hourly kernel sample, the restart ledger's boot and cut rows) only ever climbed and a fall could never show. The fix reads the current size from the Mach kernel's task_info(MACH_TASK_BASIC_INFO) through ctypes, falling to a bounded ps -o rss= (argv only, one fork per 10 s on a monotonic memo) when ctypes cannot reach it, keeps the peak visible as rss_peak_kb on darwin alone, names the reader in source (proc, task_info, ps, unavailable), and leaves Linux and every other platform's block unchanged. The tests drive the darwin branch by patching sys.platform and the readers, and the ctypes plumbing against a stand-in library, so no leg assumes a Mac; upstream's kernel has the same branch.
