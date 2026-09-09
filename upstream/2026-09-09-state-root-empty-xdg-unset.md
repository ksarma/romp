---
title: State root: an empty XDG_STATE_HOME reads as unset in every Python reader, as the shell surfaces already do
status: offered
where: upstream branch xdg-empty-offer, re-derived from fork commits bc44c344 and 5df40dc1 (fork PR #272): `postal/postal_service.py` STATE and NAMES_DIR, `kernel/event_model.py`, `kernel/judge.py`, `cli/idle_dots.py` STATE, `tests/smoke_codex_live.py` RUNTIME_STATE; tests `tests/test_state_dir_override.py` PythonSurfaces (one empty-XDG case with subtests, two new PY_SURFACES rows)
added: 2026-09-09
pr:
tier: fix
offered: their PR #1211
closed:
---
Audit row 19. Six state-root lines kept an empty XDG_STATE_HOME and so put the Python side's state under the relative path romp in the process cwd while every shell surface used the home root; the readers now fall through with an or-fallback, as the XDG spec reads an empty variable. Six one-line edits and one test case.
