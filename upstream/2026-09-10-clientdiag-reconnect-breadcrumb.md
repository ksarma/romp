---
title: Client-diag rows say which kind of socket carried them (reconnect), and the shim's wsclose row carries bundleReady, so the log tells a declared redial from one the dial term gated off
status: candidate
where: kernel/kernel.py (the clientDiag handler; the wsclose row in _shim), docs/read-side.md, tests/test_client_diag_reconnect_stamp.py, tests/test_kernel_disconnect_banner.py, tests/test_client_diag_rotation.py, ui/webview/pane-shim-stale.test.ts
added: 2026-09-10
pr:
tier: fix
offered:
closed:
---
The shim's only drop breadcrumb, the wsclose row, recorded everConnected alone, so client-diag.jsonl could not tell a declared redial (?reconnect=1) from a mid-load drop the dial term gated off, nor from a ready that reached the shim while its socket was going down. The kernel now stamps every row with the carrying socket's reconnect flag (the queued wsclose row rides the redial, ahead of the re-sent ready whose strip consumes the flag), and the row carries the shim's bundleReady at the close. Both halves exist upstream unchanged.
