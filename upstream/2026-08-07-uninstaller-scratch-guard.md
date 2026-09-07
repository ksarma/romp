---
title: Uninstaller scratch-path guard hardening (canonicalise before the checks; property tests over the spelling class)
status: merged
where: PR #2 (`180e2bea` etc.)
added: 2026-08-07
pr:
tier:
offered: their PR #387
closed: 2026-08-15
---
**The 2026-08-13 "mostly fork-only, low-severity, not an attacker vector" assessment on this row was WRONG, and was corrected by direct probe on 2026-08-14.** Upstream IS affected, and worse than the fork was: `ROMP_JUDGE_SCRATCH="$STATE"` with a plain `--yes` and no `--purge` deletes `$STATE` outright — no path mangling needed at all, because `$STATE` contains `romp` so it clears the name check and nothing refuses the state root. `"$HOME/"` deletes `$HOME` where the home path contains `romp`. Also newly found, in neither the fork commits nor the audit: `rm -rf "$link/"` cannot unlink a symlink so it recurses and EMPTIES the target directory. Two claims that did NOT hold and are not in the PR: the trailing-newline variant is inert upstream (the path does not exist, so `rm` no-ops), and `$HOME/.` aborts mid-run rather than deleting. Preconditions are honest in the PR body: `ROMP_JUDGE_SCRATCH` is an uninstaller-only override nothing in romp sets. **Ordering:** we advised landing #387 before #379; it went the other way, so between the two merges `main` briefly carried #379's `realpath` slug with no symlink guard — the validated string and the deleted target were different paths. #387 closed it on 2026-08-15. Re-proved against post-#379 `main` before merging, not against the original base.

Status detail (migrated from the table): ✅ **MERGED — their #387** (2026-08-15)
