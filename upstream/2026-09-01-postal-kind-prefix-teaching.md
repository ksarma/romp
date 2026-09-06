---
title: The postal SessionStart hook and the romp-postal skill still teach a `DELEGATE:/COORDINATE:/QUESTION:` body prefix, contradicting `send_message`'s REQUIRED `kind` parameter (delegate|coordinate|question) that the MCP server's own instructions already mandate — two instructions for one fact, one of them retired
status: candidate
where: branch `guidefixes`: `hooks/romp-postal-context.sh` (the norm bullet now says set `kind`), `claude/skills/romp-postal/SKILL.md` (tool signature `send_message(to, body, kind)`, shell form `romp mail send --kind …`, the norms bullet); `tests/romp-postal-context.bats` asserts the `kind` wording and that the prefix is gone
added: 2026-09-01
pr:
tier:
offered:
closed:
---
Upstream ships the identical texts (verified 2026-09-01 at `5c1e0cac`: `hooks/romp-postal-context.sh:13`, `claude/skills/romp-postal/SKILL.md:32`). Text-only, no behavior change. The shell CLI itself treats `--kind` as optional (`postal/postal_service.py` usage brackets it); the skill teaches the stricter norm on purpose, matching the kernel's own reply hint.

Status detail (migrated from the table): **candidate**
