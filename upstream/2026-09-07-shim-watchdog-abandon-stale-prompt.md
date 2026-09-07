---
title: The pane shim raises the stale prompt when it abandons a silent reconnected socket, and the drop bell names the pane by its rail label
status: merged
where: not on fork main: built against upstream/main as branch `shim-watchdog` (head `51eaec7a`, two commits: `ae73e845` the shim's `abandon()` runs the close rule; `51eaec7a` the bell row's pane label): `kernel/kernel.py` (the pane shim's `abandon()` and stale rule; the bell's pane-label map), `docs/read-side.md`; tests `tests/test_kernel_disconnect_banner.py`, `tests/test_ws_drop_loud.py`, `ui/webview/pane-shim-stale.test.ts`. The fork brings it home in the next upstream fold
added: 2026-09-07
pr:
tier: fix
offered: their PR #957
closed: 2026-09-06
---
The regression the #952 review found. The stale prompt has two raising events (the second keepalive on the reconnected socket before its resync, and that socket closing before its resync), but the watchdog's `abandon()` nulled `onclose` before closing a socket quiet past 30 s, so the close rule never ran for an abandoned socket: a kernel that accepted the reconnect and then never spoke on it flapped the loader every 30 s and never raised the prompt (the 1 s timer the rule replaced had raised on the first cycle). `abandon()` now runs the close rule itself, retiring the arm and raising with the arming path plus `-quiet` (`reconnect-quiet`, `foreground-quiet`); `stalePending` retired; the test captures the shim's `setInterval` and ticks the watchdog by hand; `docs/read-side.md` and the `onclose` comment say an abandoned socket leaves no `wsclose` row. The bell's dropped-connection row names the pane by its rail label.

MERGED 2026-09-06T21:04Z as their PR #957 (merge `fd2135c0`; head `51eaec7a`; label fix). Fork side: NOT on fork main, since it was built against upstream after #952 had merged; bring it home in the next upstream fold. Two items the merge comment named as out of scope are follow-up entries: the bell's `PN` map derived from `_PANE_ORDER` (`kernel-small-fixes-taskupdate-tick-pn`) and a `foreground-quiet` pin in `pane-shim-stale.test.ts` (`batch12-review-tests-only-followups`).
