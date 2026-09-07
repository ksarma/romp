---
title: The /file relay 404s every remote TEXT file (its view gate predates the text half), so the viewer fails on a federated session's .py/.md with no Download offer
status: merged
where: fork PR #61 (`main`)
added: 2026-08-14
pr: 61
tier:
offered: their PR #385
closed: 2026-08-18
---
Pure bug fix; upstream ships the same preview-only gate. The fix keeps the lying-remote defense exactly (Content-Type still derived locally — text/plain + nosniff is inert) and is pinned by a new relay test. ALREADY FOLDED into the file-links offer: #385's commit A carries the `_remote_file` text-relay widening and its test (added at port time, 2026-08-14 — without it the viewer 404s every federated text file, contradicting the PR's own federation claim), and it survived the 2026-08-15 rebase intact (interdiff-verified). Resolved with #385's merge; came home in the v0.12.0 fold (`upfold0819`), which layered upstream's resumable-206 relaying and tunnel redial onto the same `_remote_file` without disturbing the fork's mirrored save-conflict headers.

Status detail (migrated from the table): ✅ **merged — rode their PR #385** (2026-08-18)
