---
title: Tests: every test module loads the code under test with `load_source(name, path)` from `tests/romp_load.py` instead of `SourceFileLoader(...).load_module()` (removed in Python 3.15); `tools/loadsource-sweep.py` rewrites them from the AST, idempotently, and the isolation ratchet (`tests/test_state_isolation_order.py`) refuses the old idiom by file and line, naming the command that fixes it
status: offered
where: fork PR #276 (`ft-sweep`, merged 2026-09-07 with the `ft-ready` stack, merge `c94e97a9`): `tools/loadsource-sweep.py`, `tests/test_state_isolation_order.py`, 537 converted test files
added: 2026-09-07
pr: 276
tier: docs
offered: their PR #1283
closed:
---
Upstream's test tree has 508 modules on the old idiom (`git grep -l SourceFileLoader upstream/main -- tests`, 2026-09-07); on 3.14t each import warns and on 3.15 each fails. The script edits from the AST, never text inside a string or comment: every `X(...).load_module()` where X is bound by `from importlib.machinery import SourceFileLoader [as X]` becomes `load_source(...)` with the arguments verbatim; an import whose name is no longer used is dropped or replaced by `from romp_load import load_source`; a module that converted a call and has no top-level import of `load_source` gets one after the last import before its first load; a name still used in code (a mock patching it) keeps its import. A converted file is left alone, and `--check` rewrites nothing and exits 1 when a file would change.

Must be REGENERATED on upstream's tree, not cherry-picked: the conversion touches every test file, so it lands last, after the readiness entry (`free-threaded-readiness`, fork #275, which adds `kernel/loadsource.py` and `tests/romp_load.py`), by running the script there and committing its output; upstream's newer test modules that the fork lacks convert the same way, and a later branch that lands test files in the old idiom is fixed by running the script again. Until it lands, the old idiom's DeprecationWarnings on 3.14t are expected.

Filed 2026-09-10 as their PR #1283: three commits (tool plus two ratchets, the regenerated 591-file conversion, three hand edits), on the tip after their #1278 (the loader) merged; the conversion is regenerated on the exact base if it goes stale.
