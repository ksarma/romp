---
title: Gear: the update notices help line says an automatic converge restarts at once (T269), not at the next quiet moment
status: candidate
where: ui/webview/gear.js (the Updates and update notices help line); the docs/reference.md paragraph is fork-only; pin in tests/test_kernel_update.py
added: 2026-09-09
pr:
tier: docs
offered:
closed:
---
T269 (upstream #1121) made every deploy restart immediate and left `romp refresh --quiet` as the one door to a quiet window, but the gear's help line for Install automatically still says it converges "restarting at the next quiet moment": upstream's ui/webview/gear.js at bcc7e215 line 160 carries that sentence, and the automatic converge there calls the same immediate restart the fork's does. The fork's line (this fold, the reviewer's ruling) says the mode converges by itself and restarts at once, with turns in flight cut and resumed with their history; the sentence the offer carries is that clause alone. The docs/reference.md paragraph the fork changed beside it is fork-authored and stays here. The pin, tests/test_kernel_update.py Wiring::test_the_copy_says_an_automatic_update_restarts_at_once, reads the gear source and the reference paragraph; an offer carries its gear half.
