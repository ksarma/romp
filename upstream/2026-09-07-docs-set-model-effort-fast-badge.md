---
title: Docs pair: `set_model` / `set_effort` say what the tmux side can and cannot report, and `docs/reference.md` places `/fast` on its badge
status: approved
where: not built; from the maintainer's review comment on their PR #950 (2026-09-06): `kernel/session_backend.py` `set_model` / `set_effort` docstrings (the 'False when it can't be applied' clauses), `kernel/kernel.py` `TmuxBackend.set_model` / `set_effort` (return True unconditionally), `docs/reference.md` (the model-and-effort section that lists `/fast on|off`)
added: 2026-09-07
pr:
tier: tests-only
offered:
closed:
---
The contract promises False for an unknown sid or a bad value but only `SdkBackend` does that; a clause should say the tmux side cannot tell, so callers validate first (as `_route_meta_command` does). `docs/reference.md` places a typed `/fast` under the model and effort dropdowns; the fast toggle is the separate badge the next section describes. Docs-only, labelled tests-only like #950.

APPROVED 2026-09-07: the fork owner said offer it (batch 13, tier tests-only). Fork side, open fork PRs #272, #273 and #258 touch `docs/reference.md`.
