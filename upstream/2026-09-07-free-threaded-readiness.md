---
title: Free-threaded CPython readiness (3.14t): the kernel's shared caches close their check-then-act and read-modify-write races, `SourceFileLoader.load_module()` (removed in Python 3.15) gives way to `kernel/loadsource.py`, CI gains a 3.14t cell, and the test floors poison `ROMP_KERNEL_PORT` / `ROMP_SERVE_PORT` beside `ROMP_MANAGER_PORT`
status: candidate
where: fork branch `ft-ready` (kernel/kernel.py, kernel/judge.py, kernel/event_model.py, kernel/loadsource.py, tests/romp_load.py, tests/test_free_threaded_caches.py, tests/conftest.py, tests/__init__.py, .github/workflows/ci.yml, docs/install.md)
added: 2026-09-07
pr:
tier:
offered:
closed:
---
Three of the races are live under the GIL and upstream carries the same code: `_cached_feed` read the payload slot twice while the parse-warm thread cleared it (a None reached `_push`'s wire loop, outside its try, and ended the pusher thread); two passes over `_parked_creates` re-ran one comment create and the loser's `.remove` raised; the pending tag journal's read-modify-write spanned two lock sections and lost a queued edit after its client was told "queued". The rest (the msg-summary table, the names-memo sweep, the tmux echo store, the judge-usage reader, the once-per-episode retry gate, the pin-association memo, the click stamps, the path-link cache, the counters) are likely only without the GIL. Every fix has a test that fails against the tree before the thread-safety commit with the loader change applied (`39c8e800`: all 19 fail with the GIL off, 16 of 19 with it on, where the three plain-counter tests pass; the module imports tests/romp_load.py, so a tree without the loader commit cannot collect it). Two fork branches, two offers if offered: `ft-ready` (this row) converts the kernel modules and tools and adds the helper (kernel/loadsource.py keeps `load_module()`'s sys.modules reuse, which `km.jd is jd` in every test depends on); the follow-up branch `ft-sweep` converts the 532 test files with tools/loadsource-sweep.py (idempotent; run the script on upstream's tree rather than cherry-pick the result) and tightens the ratchet to forbid the old idiom. Until the sweep lands, the old idiom's DeprecationWarnings on 3.14t are expected.

Status detail (migrated from the table): candidate
