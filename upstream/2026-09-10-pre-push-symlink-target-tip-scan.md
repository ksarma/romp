---
title: The pre-push hook reads each symlink's target in a pushed tip (git grep skips 120000 blobs), so an inherited link into a home path is refused like its regular-file twin
status: offered
where: .githooks/pre-push (the tip pass, after the git grep block), tests/pre-push-hook.bats (seven symlink cases), CLAUDE.md (one phrase)
added: 2026-09-10
pr:
tier: fix
offered: their PR #1271
closed:
---
Divergence-audit row 18. Re-derived onto the project's flat loop from the fork's per-commit scan (fork PRs 53 and 222). The gitleaks hook arm (row 39) stacks on this branch.
