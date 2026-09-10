---
title: Chat: switching to a loading tab re-measures the jump and reply chips (showActive's no-session branch ends with updateJumpBtn; updateJumpBtn yields to the set with no live session), so the leaving tab's chips do not stay over the loader
status: merged
where: ui/webview/render.ts (showActive, updateJumpBtn), ui/webview/skeleton-tabs-wiring.test.ts (three executing cases plus pins)
added: 2026-09-10
pr:
tier: fix
offered: their PR #1255
closed: 2026-09-10
---
Pre-existing defect narrowed by their #1226 and recorded in its review: a tab left at the top of a long transcript fired no clamp and no resize on the switch, so its chips stayed painted over the new tab's loader and a stale click parked a wrong anchor. Filed directly from the upstream base.
