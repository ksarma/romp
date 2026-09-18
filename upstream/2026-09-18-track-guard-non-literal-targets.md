---
title: The tracked-changes bash guard refuses non-literal write targets in a tracked repo
status: candidate
where: hooks/romp-track-bash-guard.mjs and its tests
added: 2026-09-18
pr:
tier: fix
offered:
closed:
---
The Bash-side track guard (a PreToolUse hook on the Bash tool) blocked a shell write to a tracked file only when the target path was literal in the command: a cp whose destination was a shell variable, a command substitution, a backtick, a ~user, a brace list past the cap, or a glob it could not expand went through and overwrote the tracked file with no change recorded, while the same command spelled out was refused (a research session reported it through the box admin, 2026-09-17). The hook now refuses such a target while a project that tracks anything is in play (the session cwd, the directory a cd moved to, or the folder a copy lands in has a .trackchanges/config.json with a non-empty tracked list), with a message that says the target is not literal, that a tracked file takes its change through track-edit, and to spell the path out or write outside the project; it never reads the session environment to resolve the word. Found on the way: a redirection onto several glob matches or brace alternatives was read as the ambiguous redirect bash refuses, but zsh (multios) writes each, so the hook now names each. Literal targets keep their verdicts; commands with no tracked project in play are untouched. Tests in tools/romp-track-bash-guard.test.mjs, the shapes module, the plan pins and the vendored skill patch 0009.
