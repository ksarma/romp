---
title: romp perf export --public and romp restart-metrics --json --public: one paste-safe copy of the performance counters, from a shared shape module
status: candidate
where: cli/perf_export.py, cli/perf_public.py, cli/restart_metrics.py, bin/romp (perf block), bin/romp-perf-export, docs/reference.md; tests in tests/test_perf_export.py, tests/test_restart_metrics.py, tests/romp-perf.bats, tests/test_perf_stats.py
added: 2026-09-18
pr:
tier: feature
offered:
closed:
---
Stage two of the usage-data answer (2026-09-18): a raw GET /perf snapshot cannot be pasted in an issue, so a verb writes its public form instead. cli/perf_public.py holds the rules shared by the export, by restart-metrics and by the served-snapshot invariant test: the browser's ident grammar over every key and string value (else other, colliding keys merged), the kernel's route register for the http block (a checked-in copy held equal by a test; an older kernel's raw family paths collapse as the kernel does now), the joined-identifier byte tables, a denylist of key paths (the read table by path, the child's first failure, the stacks, pids and clock stamps, every key naming a session, a place, a host or a user), the invariant walk and an identifier scan for the strings only the machine knows (hostname, user, home, the registry's sids and working directories), which refuses the write naming the key path and never the value. The export adds a schema line (romp-perf-export/1), the UTC minute and the kernel's abbreviated commit when the snapshot carries one, writes perf-exports/perf-export-<YYYYMMDDTHHMM>.json at 0600 under the state directory or --out, reads --from a saved snapshot, adds a usage block on --usage (session counts, actions and views from the http counts, the uptime bucket), and refuses without --public: there is no raw mode. Nothing leaves the machine; the upload verb the answer designs is not built. The offer waits on the no-new-upstreaming hold.
