---
title: `romp-manager`'s scoped tmux start: an ETIMEDOUT line stops predicting an unscoped server
status: offered
where: not built; from the maintainer's review nit on their PR #953 (2026-09-07T00:23Z): `bin/romp-manager` `startTmuxServer`'s failure line after an ETIMEDOUT on the scoped call
added: 2026-09-07
pr:
tier: fix
offered: their PR #967
closed:
---
After an ETIMEDOUT on the scoped `systemd-run` call the line says the server is starting the plain way, but tmux may already have daemonized inside the scope, so the line can predict a loss that will not happen. Probe the server (or the scope) before choosing the wording, or word the line as uncertain.

APPROVED 2026-09-07: the fork owner said offer it (batch 13, tier fix). #953's head `590ba7dc` is not on fork main (`origin/scopes-offer` is gone): build off upstream/main. Fork side, open PRs #272 and #258 touch `bin/romp-manager`.

OFFERED 2026-09-07: offered upstream as their PR #967 (2026-09-07, label fix, head 74db19a3); one PR for six entries: `stale-setting-toast-liveness`, `kernel-small-fixes-taskupdate-tick-pn`, `find-orphan-clis-own-pid`, `note-served-model-no-modelusage`, `github-link-ls-remote-askpass`, `manager-scoped-tmux-etimedout-line`.
