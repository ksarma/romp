---
title: The pre-push hook runs gitleaks over the commits a push publishes (merge commits by first-parent diff), refusing a credential the way it refuses an identifier; .gitleaks.toml allowlists the RFC 6455 nonce by value; ROMP_NO_GITLEAKS and ROMP_GITLEAKS switches
status: merged
where: .githooks/pre-push (scan_identifiers wrapper, scan_credentials), .gitleaks.toml (new), tests/gitleaks-config.bats (new), tests/install-sh.bats, tests/pre-push-hook.bats, CLAUDE.md, CONTRIBUTING.md
added: 2026-09-10
pr:
tier: feature
offered: their PR #1276
closed: 2026-09-10
---
Divergence-audit row 39 PR A (fork PRs 1 and 4), re-derived onto the project's hook after its symlink tip pass (their #1271). The CI secrets job is PR B, their PR #1279, stacked on this branch and filed without auto-merge (touches .github/).
