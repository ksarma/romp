---
title: Raise gc threshold[2] once at boot
status: candidate
where: kernel/kernel.py (_raise_gc_gen2_threshold, _gc_gen2_threshold_knob, _gc_gen2_threshold_reason and _GC_THRESHOLD_SAID beside _GC_SAID; the call in main beside install_gc_hook); docs/reference.md (the gc bullet)
added: 2026-09-19
pr:
tier: fix
offered:
closed:
---
A full collection in CPython needs counts[2] over threshold[2] AND promotions over a quarter of the long-lived total; at the default 10 the count gate never bound (175 against 10 on a production kernel at 6.8 h up), so the quarter rule alone timed full collections: 103 an hour, mean 2.97 s, 8.5% of a core in pauses holding the interpreter lock. The kernel now sets the third threshold once at boot (ROMP_GC_GEN2_THRESHOLD, default 1,000, derived from the measured 5.6 generation-1 collections a second and a 180 s gap; 0 keeps CPython default), gated on the interpreter build facts (the free-threaded build and CPython 3.14.0 to 3.14.4 decline with one stderr line) with a read-back post-condition. Tier is the consolidator call: fix (8.5% of a core in stalls on every page) or feature (it adds a knob).
