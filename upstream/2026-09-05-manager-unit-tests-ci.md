---
title: The manager's unit tests (`tests/manager-*.test.js`: drain, registry, restart, tmux scope) ran nowhere in CI — pytest, `bats tests/*.bats` and the extension's `npm test` covered everything else
status: resolved-upstream
where: fork branch `scopes`: `.github/workflows/ci.yml` (a `node --test tests/manager-*.test.js` step in the vscode-extension job, which already sets up Node)
added: 2026-09-05
pr:
tier:
offered:
closed: 2026-09-02
---
CLOSED 2026-09-06 without an offer: upstream’s ci.yml already runs `node --test tests/manager-*.test.js` (their T224 follow-up to our #868); the gap was fork-side only. Upstream's `ci.yml` has the same three suites and the same gap for its three manager suites. One step, no new pin: the job's Node 22 runs them from the repo root.

Status detail (migrated from the table): ✅ **resolved upstream** — their T224 (2026-09-02)
