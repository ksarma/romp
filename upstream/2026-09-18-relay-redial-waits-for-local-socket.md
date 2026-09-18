---
title: Relay redials wait for the local socket
status: approved
where: kernel/kernel.py (the pane shim netState publishes window.__rompLocalUp); ui/webview/federation.ts connect (the deferral and its dial-deferred row), start and watchLocalLink/localUp (the romp:wsup listener), poll (the /tunnels gate); tests: tests/test_pane_shim_return.py LocalUpFlag (three cases; the third reads the flag inside each romp:wsup dispatch), tests/test_client_diag_allowlist.py (the dial-deferred fixture row), ui/webview/federation-reconnect.test.ts (the seven new cases, from 23 to 30 in the file, and the extended start() pin)
added: 2026-09-18
pr: 765
tier: fix
offered:
closed:
---
A federated pane dials its relay (/remote/<host>/ws on the same origin) the instant it is foregrounded, so with the local socket down the handshake hangs, the relay watchdog cuts it at 15 s and dials again: 55 watchdog-close connecting rows in 23 minutes on the user's phone (2026-09-18). The shim now publishes its socket state as window.__rompLocalUp beside its wsState post; connect() defers the dial while the flag is false (one hostconn dial-deferred row per conn per down spell, fixed identifiers only, keys the allowlist already admits), the local socket's romp:wsup redials every live conn whose socket is null or CLOSED and runs one poll, and poll() reads no /tunnels while the flag is false. The foreground kill, the watchdog abandon and socketVerdict are unchanged. Undefined (a page without the shim, VS Code) dials as before. Fork PR stacked on the beacon extension; the offer waits on the user's word under the standing no-new-upstreaming rule.

2026-09-18: approved for offer by the user (the plan's list of offers needing the user's word first); alone, with the diag row.
