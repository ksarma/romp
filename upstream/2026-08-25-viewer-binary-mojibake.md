---
title: The file viewer opens images and PDFs as line-numbered mojibake — its fetch pipeline calls `r.text()` on ANY 200, so a clicked .png renders as garbage; fix branches on the kernel's own Content-Type verdict (image/* → the fetched bytes as ONE `<img>` at an object URL revoked on every teardown, SVG via `<img>` only; application/pdf → the lightbox's iframe treatment), hides the text-only affordances (Wrap, comments) over media, and pins the kernel's image-200 contract (image mime + no X-Romp-Text-Utf8) from both sides
status: merged
where: fork branch `imageview` (ui/webview/file-view.ts + both sheets; pins in ui/webview/file-view.test.ts + tests/test_kernel_preview.py)
added: 2026-08-25
pr:
tier:
offered: their PR #733
closed: 2026-08-27
---
MERGED as-is (head is an ancestor of their main, verified same night). Branch retired. OFFERED 2026-08-27 (branch `view-binary`, `2407d8c5` off tip `14a4bd70`): re-derived from origin/main’s post-fold viewer; review’s one mustFix was real — upstream’s 2026-08-26 css-vocab token sweep retires the fold-era raw box-shadow literal, fixed to var(--shadow-modal) in both sheets; red-first 10 media tests fail on base; scaffold CI green (since-closed fork #119). Upstream ships the identical `r.text()` pipeline in the same shared file, so their viewer has the same mojibake on every image click. Self-contained: the kernel needs nothing — it already serves images correctly (locally-derived mime, nosniff, the 50 MB/413 cap, 206 ranges, an image-faithful relay).

Status detail (migrated from the table): ✅ **merged** — their PR #733, merged as-is 2026-08-27 (merge `478b0c1c`)
