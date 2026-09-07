---
title: The picker's Browse… (and the chat's 📎) do nothing on any non-macOS kernel
status: landed
where: PR #25
added: 2026-08-08
pr:
tier:
offered: their PR #258
closed: 2026-08-10
---
Upstream ships the same `_pick_folder`/`_pick_file`: an `osascript` call whose `OSError` is caught and returned as `None`, so off macOS the click sends `browseDir`, gets no reply at all, and the button looks alive while doing nothing. Found on a headless Linux kernel (the user 2026-08-08). Fix adds the Linux pickers (zenity/qarma/yad/kdialog, gated on `DISPLAY`/`WAYLAND_DISPLAY` — an installed picker with no screen hangs, which is the same silent nothing), advertises `nativeDialogs` on `sessionList` + `/defaults` so the UI drops a button that cannot work, and warns instead of swallowing a click it can't serve. Pure bug fix, no fork-specific content; anyone running the kernel on Linux hits it.

Status detail (migrated from the table): **landed** — their PR #258 MERGED 2026-08-10, in v0.7.0
