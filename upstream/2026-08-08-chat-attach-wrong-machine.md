---
title: The chat's 📎 opens the picker on the wrong machine from a remote browser; oversize attachments vanish silently; a remote session's attachment bytes land on the wrong kernel
status: landed
where: PR #29
added: 2026-08-08
pr:
tier:
offered: their PR #258
closed: 2026-08-10
---
Follows #25 one layer up, the same split #26 made for file links: upstream's desktop 📎 posts `pickFile`, so a native dialog opens on the KERNEL's screen — the wrong machine whenever the dashboard is read from another device, and on a headless kernel only a warning. Fix routes by host: the web dashboard opens the BROWSER's own picker (the hidden `<input type=file>` flow touch already used, unscoped + multi-select on desktop, still photo-scoped on phones) and ships bytes over the existing `dropFile` path; the VS Code webview keeps the host dialog, which is correct there. Also: the 50 MB `shipFileToHost` cap used to `return` silently (a big drop just vanished) — now a toast names the file, its size and the cap; and `dropFile` now carries the session id so federation routes the bytes to the kernel that OWNS the session (the saved `drops/` path rides the prompt and is read by the agent on that machine — before this, a remote session's attachment saved onto the viewer's local kernel and handed the agent a nonexistent path). Pure bug fixes, no fork-specific content.

Status detail (migrated from the table): **landed** — their PR #258 MERGED 2026-08-10, in v0.7.0. Upstream then added the pending-attachment chip (up at pick time, retired by the `droppedPath` ack / new `dropSaveFailed` nack), adopted back on the fork in the v0.7.0 merge
