---
title: The manager requires the serve token on every state-changing control-port request
status: candidate
where: bin/romp-manager kernel/kernel.py vscode-extension/src/extension.ts docs/reference.md bin/README.md tests/manager-token.test.js tests/test_manager_write_token.py tests/romp.bats tests/manager-down.test.js tests/romp-manager-ensure.bats tests/romp-manager-tmux-scope.bats
added: 2026-09-10
pr:
tier: fix
offered:
closed:
---
Upstream's manager has the same open doors: POST /restart-all, /restart, /stop and /ensure answer anything on loopback with no token, so any local process can restart every session (it happened here on 2026-09-10). An offer carries the gate (writeGate: X-Romp-Token compared against the serve-token file, read per request; 401 for a missing or wrong header, 503 while the file is unreadable, one log line per refusal naming the address and the door), the header on every caller upstream ships (the manager's control client behind the romp verbs, the kernel's two loopback hops and the self-update script's curl on stdin, the extension's /ensure), the docs, and the tests with their fails-before.
