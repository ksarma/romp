---
title: Per-session env vars at spawn (`romp new --env NAME=VALUE`, repeatable, riding POST /new into the per-sid flag-settings payload)
status: merged
where: fork branch `sessenv`
added: 2026-08-17
pr:
tier:
offered: their PR #889
closed: 2026-09-03
---
MERGED with a privacy tightening folded on: per-session env VALUES stay private (0600 settings file; the parked chip names variables, not values). FOLD FLAG RESOLVED at upfold0905 (2026-09-05): the `os.chmod(p, 0o600)` after the settings write and the names-only parked `/env` chip (`/env (cleared)` for an empty set) adopted; `tests/test_session_env.py`'s chip pins follow. Branch retired. OFFERED 2026-09-02 (branch `sessenv`, `b3d1b23c` off tip `31d8731b`; the feature itself is already on fork main — this row’s "fork branch" pointer was stale): _apply_new_session_prefs edited minimally to stay clear of open #882’s docstring hunk; review caught one fork-provenance comment, reworded; scaffold CI green (since-closed fork #168). Upstream ships the same flag-settings layer and the same directory-scoped-only env: a `.claude/settings*.json` `env` block reaches every session in the repo and outlives the session, so two SDK sessions in one directory cannot run with different environments. Spawn-time slice only (no live-mutation op, no UI). Names validated at both doors (CLI usage error, /new 400), reg persistence beside model/effort, fork inheritance like model/auth, and reconnect re-assertion by construction (the settings file is rewritten from the reg at every connect). Pinned red-first: bats for the CLI parsing, python for /new validation, the flag-settings merge and its ""-when-empty contract, set_env, and fork inheritance. Pure feature, no fork-specific content.

Status detail (migrated from the table): ✅ **merged** — their PR #889, 2026-09-03 (our head an ancestor + his `01b0baa7` fold: the settings file is 0600 and the parked chip names vars only) — ✅ came home in upfold0905 (2026-09-05)
