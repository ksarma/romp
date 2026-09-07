---
title: `romp-manager`'s scoped tmux start: an ETIMEDOUT line stops predicting an unscoped server
status: approved
where: not built; from the maintainer's review nit on their PR #953 (2026-09-07T00:23Z): `bin/romp-manager` `startTmuxServer`'s failure line after an ETIMEDOUT on the scoped call
added: 2026-09-07
pr:
tier: fix
offered:
closed:
---
After an ETIMEDOUT on the scoped `systemd-run` call the line says the server is starting the plain way, but tmux may already have daemonized inside the scope, so the line can predict a loss that will not happen. Probe the server (or the scope) before choosing the wording, or word the line as uncertain.

APPROVED 2026-09-07: the fork owner said offer it (batch 13, tier fix). #953's head `590ba7dc` is not on fork main (`origin/scopes-offer` is gone): build off upstream/main. Fork side, open PRs #272 and #258 touch `bin/romp-manager`.
