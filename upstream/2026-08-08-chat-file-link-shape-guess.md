---
title: Chat file links are shape-guessed, so a bare `render.js` becomes a link that 404s on click
status: landed
where: PR #28 (`linkresolve`)
added: 2026-08-08
pr:
tier:
offered: their PR #257
closed: 2026-08-10
---
Upstream ships the same shape-only linkifier (`CLICKABLE_PATH_RE` + the looksLike gates) with nothing checking existence. Fix resolves every path-shaped token kernel-side at message-build time (exact stat → unique `git ls-files -co` suffix → unique basename; ambiguity never guessed) and ships `{token: real target}` as `pathLinks` on the chat event; the client keeps all its shape gates and adds map membership, so shortened mentions are FIXED to their real file and phantom paths stay prose. Includes the `/file` error bodies naming the resolved path and the 2.0 MB text cap. Old events without the key keep today's behavior, so it degrades cleanly. Pure fix, no fork-specific content.

Status detail (migrated from the table): **landed** — their PR #257 MERGED 2026-08-10, in v0.7.0
