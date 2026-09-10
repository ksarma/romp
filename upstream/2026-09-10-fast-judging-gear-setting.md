---
title: Judges: a Fast judging kernel setting (STATE/judge-fast, the gear's Judges section, setJudgeFast op, fan-out) adds Claude Code's fastMode opt-in to Opus judge calls through the one --settings overlay
status: offered
where: kernel/judge.py, kernel/kernel.py, ui/webview/gear.js, ui/webview/federation.ts, docs/reference.md, docs/judges.md, six test modules
added: 2026-09-10
pr:
tier: feature
offered: their PR #1292
closed:
---
Divergence-audit row 35 (fork commit 4c3b62bf, no fork PR number), re-derived onto the project's kernel-setting shape (not the fork's per-install one); the body offers the per-install shape as the alternative. Collides with #994 at three sites; whichever lands second rebases.
