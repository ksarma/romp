---
title: The materialized-atom LRU kept the entries of freed atom lists until its cap, which on a large machine never binds: a tree read after its index was released registered entries nothing removed, so the LRU grew by the entries of every such tree (6.15 million against a 7.73 million cap after 73 hours on one machine, most of them for freed lists); each list now carries a weak reference whose callback only queues it, the next registration or release drains the queue under the lock and removes that list's entries, and /perf asmIndex gains collected, the count the drain removed
status: candidate
where: kernel/event_model.py (_MAT_LRU comment, _MAT_COLLECTED, _ListRef, _mat_collected, _ASM_INDEX_STATS, _mat_register, _mat_trim, _mat_drain, LazyIndex docstring, LazyIndex.__init__, LazyIndex.release, LazyAtoms docstring, LazyAtoms.__init__, LazyAtoms._at, LazyAtoms.clear, LazyAtoms.reverse, LazyAtoms.__iadd__, LazyAtoms.__imul__, asm_index_stats), docs/reference.md, tests/test_asm_mat_lru_release.py, tests/test_perf_stats.py, upstream/2026-09-24-atom-lru-collection-event.md
added: 2026-09-24
pr:
tier: fix
offered:
closed:
---
Upstream ships the same LRU (weak ownership, no weakref callback, dead entries left for the cap), so the growth and the fix apply as they are. fix tier: the tests in tests/test_asm_mat_lru_release.py are red on the unfixed event model for the stated reason ((live, dead) entry counts such as (1, 5) != (1, 0)). The cap is unchanged; it stays a backstop above the live entries.
