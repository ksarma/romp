---
title: PR tier label check and PR template
status: resolved-upstream
where: fork branch pr-tier-check (9fee0c13), scaffold #198 closed 2026-09-07
added: 2026-09-07
pr:
tier: fix
offered:
closed: 2026-09-07
---
A required check that every PR carries exactly one tier label (fix, tests-only, feature, major-feature) and a PR template that asks for it. Built on fork branch pr-tier-check with scaffold #198 for CI; never offered, because it was held for the maintainer's answer to the tier brief.

RESOLVED UPSTREAM 2026-09-07: the check and template landed on main as 189f56ee (2026-09-06); the maintainer's #991 (discussion #989) makes the tier policy a required check on top of it and renames tests-only to docs. Nothing left to offer.
