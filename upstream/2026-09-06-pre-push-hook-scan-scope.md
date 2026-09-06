---
title: The pre-push hook scanned every commit in a ref's update range by TREE, so once a denylisted string had landed on main (and been redacted there), every branch cut from main in between was refused: its commits inherit the string in their trees, and a branch that merged main also carried main's own commits in `remote_sha..local_sha` (2026-09-06: two identifiers added to the fork's list, redacted forward in fork PR #209; 22 branches on the fork's remote had inherited them)
status: candidate
where: branch `privfix`: `.githooks/pre-push` (`rev_range`, `added_lines`, `scan_identifiers`), `tests/pre-push-hook.bats`
added: 2026-09-06
pr:
tier:
offered:
closed:
---
Upstream ships the same hook with the same per-commit tree scan over `remote_sha..local_sha` (theirs is the identifier-only variant: no gitleaks pass, no symlink scan). Two changes: (1) per pushed ref, the TIP tree must be clean (the exposure a push creates) and each new commit must ADD no banned line in its first-parent diff, so an introduction inside an intermediate commit is still caught and named while a commit that only inherits an older leak is not; (2) the range excludes commits reachable from the pushed-to remote's refs (`<local> --not <remote_sha> --remotes=<remote>`), scoped to that remote, falling back to the old range when the clone has no remote-tracking refs for it. About 40 lines; the bats cases port only if they take the test file too (upstream has no `tests/pre-push-hook.bats`). This file's header lists the private-strings hooks as fork-only infrastructure; the hook itself is tracked upstream, so the row stands and the header is the user's call.

Status detail (migrated from the table): candidate
