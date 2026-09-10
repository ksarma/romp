---
title: Update banner: the Update button takes two clicks (the first arms it as the restart it runs, naming the sessions it stops and interrupts over every backend, with a Cancel; the second posts, and a double-click never does), the kernel refuses POST /update without confirmed:true, and the audit row carries via: update-confirmed
status: candidate
where: kernel/kernel.py (_UPD_HTML, _UPD_CSS, _UPD_JS, the /update and /update-check routes, _restart_impact, the shell's --err token), kernel/sdk_backend.py (SdkBackend.restart_impact, _restart_disrupts), kernel/codex_backend.py (CodexBackend.restart_impact), docs/reference.md, tests/test_update_banner_confirm.py (new: node executes the served script; Playwright legs in Chromium and Firefox), tests/test_kernel_update.py (Routes), tests/test_sdk_busy_count.py, tests/test_codex_backend.py
added: 2026-09-10
pr:
tier: fix
offered:
closed:
---
A click that only meant to focus the dashboard window landed on the banner's Update button (2026-09-10) and one click restarted every session on the box, cutting every turn in flight. Upstream serves the same banner from the same kernel code. The armed state is dropped by exact events only (Cancel, a press outside the banner in the shell document, focus leaving the armed button, the window's blur, a hidden tab, every re-render of the banner), never a timer, and the armed click ignores the second click of a double-click (the browser's own click count). The counts sum every backend the kernel runs (Claude and Codex sessions, each backend's restart_impact of one shape) and count as interrupted the sessions the restart gate's busy predicate names (a turn in flight or live background work); the label carries no counts while the SDK backend is still being built.
