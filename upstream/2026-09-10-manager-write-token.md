---
title: The manager requires the serve token on every state-changing control-port request
status: candidate
where: bin/romp-manager bin/romp kernel/kernel.py vscode-extension/src/extension.ts vscode-extension/src/kernel-attach.ts docs/reference.md bin/README.md plans/multi-kernel.md tests/manager-token.test.js tests/test_manager_write_token.py tests/test_fleet_restart.py tests/romp.bats tests/manager-down.test.js tests/romp-manager-ensure.bats tests/romp-manager-tmux-scope.bats vscode-extension/src/kernel-attach.test.ts
added: 2026-09-10
pr:
tier: fix
offered:
closed:
---
Upstream's manager has the same open doors: POST /restart-all, /restart, /stop and /ensure answer anything on loopback with no token, so any local process can restart every session (it happened here on 2026-09-10). An offer carries the gate (writeGate: X-Romp-Token compared against the serve-token file, read per request; 401 for a missing or wrong header, 503 while the file is unreadable, one log line per refusal naming the address and the door), the header on every caller upstream ships (the manager's control client behind the romp verbs, the kernel's two loopback hops and the self-update script's curl on stdin, the extension's /ensure), the docs, and the tests with their fails-before. Review round 1 (2026-09-10) added: the gate accepts every managed kernel's token (each kernels.json profile's own stateDir file), the manager mints the primary's token file when nothing is at the path at start, the kernel's two hops and the /restart handler surface a refusal (stderr, an audit row, a bell notice; the handler acks only what the manager took), the extension tells a refusal from no manager and toasts the fix, and `romp down` prints a refused /stop with its status and remedy instead of polling.
