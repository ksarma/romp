---
title: `tools/perf-bench.py`: an offline bench that loads the kernel in-process against a copy of a state directory and times the payload builders (`build_feed`, `build_timeline` bars and skeleton, `build_session` cold, event-model-warm and warm, `load_goals`, `Sessions.live`, `discover`, the cold, connect and steady push cycles), with `--profile` cProfile tables per builder and `--compare A.json B.json` for exact deltas
status: offered
where: fork PR #200 (`romp-perf-bench`, merged 2026-09-06): `tools/perf-bench.py`; tests `tests/test_perf_bench.py` (9 tests that drive the tool as a subprocess against a synthetic state directory)
added: 2026-09-07
pr: 200
tier: feature
offered: their PR #1057
closed:
---
Upstream's pusher CPU fixes were each verified with a hand-run profiler on a live kernel; this gives HEAD and a candidate branch the same input, without a restart and without side effects. Isolation: the state root is rebound to the copy, the manager port poisoned, the supervised env unset, every `ANTHROPIC_*` variable dropped, a private tmux socket dir used, and `kernel/kernel.py` loaded in-process with no threads. Liveness: a constructor-free `SdkBackend` subclass rebuilds the live map from the copy's registry and state logs so the builders take their live code paths, and an empty or shrunken world fails loudly instead of benchmarking nothing. Guards: `subprocess` is tripwired in the kernel, judge, SDK backend and event model (only `git rev-parse` and `git ls-files` pass, counted; `--no-git` refuses even those), notification and network functions are replaced by recorders, `pwd` lookups are counted, `_atomic_write` must land under the copy, and the copy is fingerprinted before and after with every write listed. The live default state directory is refused without `--i-know-this-is-live`, and even then a temporary mirror without credential files is benched and removed. Measured on a 31-session copy with 386 MB of transcripts: a steady pusher cycle 350 ms at HEAD against 4350 ms at the revision the kernel ran one restart earlier.

Standalone tooling with no kernel change, but the tool follows the fork's kernel shape (the slot-aware frame labeller from B16, entry `view-delta-identity-short-circuit`; the `_live_scope.sessions` slot from P3, entry `tick-jobs-wake-memos-discover-once`), so an offer is cut against upstream's tree at that time and its rows re-checked there. The tests remove every temp directory they create.

OFFERED 2026-09-08: offered upstream inside bundle PR #1057 (Tools: offline performance benches for the kernel's payload builders and the dashboard panes; label feature; branch dev-bench-offer; head 6db5b129) with `ui-bench-tool`.
