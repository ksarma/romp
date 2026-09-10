---
title: Update banner: the Update button takes two clicks (the first arms it as the restart it runs, with the live and mid-turn session counts and a Cancel; the second posts), the kernel refuses POST /update without confirmed:true, and the audit row carries via: update-confirmed
status: candidate
where: kernel/kernel.py (_UPD_HTML, _UPD_CSS, _UPD_JS, the /update and /update-check routes, _restart_impact), kernel/sdk_backend.py (SdkBackend.restart_impact), docs/reference.md, tests/test_update_banner_confirm.py (new, node executes the served script), tests/test_kernel_update.py (Routes, three tests), tests/test_sdk_busy_count.py
added: 2026-09-10
pr:
tier: fix
offered:
closed:
---
A click that only meant to focus the dashboard window landed on the banner's Update button (2026-09-10) and one click restarted every session on the box, cutting every turn in flight. Upstream serves the same banner from the same kernel code. The armed state is dropped by exact events only (Cancel, a press outside the banner, the window's blur, a hidden tab, every re-render of the banner), never a timer.
