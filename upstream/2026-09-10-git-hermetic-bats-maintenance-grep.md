---
title: Tests: the git floor's trace pins match git's maintenance spawn line, not a bare word the fixture paths carry
status: merged
where: tests/git-hermetic.bats
added: 2026-09-10
pr:
tier: docs
offered: their PR #1349
closed: 2026-09-10
---
From the maintainer's review record on their #1329: the two trace pins take the spawn-line form; the scratch root, the commit message and two positive greps carry the word so the bare form is red on every run; the --receive-pack stand-in stays unquoted by git's contract for that option.
