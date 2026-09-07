---
title: The GitHub-link `ls-remote` child cannot pop an askpass prompt
status: approved
where: not built; from the maintainer's review comment on their PR #947 (2026-09-07T00:23Z): `kernel/kernel.py` `_git_net_out`'s env, which sets only `GIT_TERMINAL_PROMPT=0` today
added: 2026-09-07
pr:
tier: fix
offered:
closed:
---
The child inherits `GIT_ASKPASS`, `SSH_ASKPASS` and `core.askPass`, so a kernel started from a terminal exporting an askpass program pops a GUI prompt on every open of a file whose private origin wants credentials (reproduced against a local 401 stand-in; the 3 s kill removes it). Add `GIT_ASKPASS=""` and `SSH_ASKPASS_REQUIRE="never"` to the same env dict with a test on the env, and make the `_git_net_out` docstring state the chosen behaviour (it says ssh fails instead of waiting, which does not hold on this path; VS Code's askpass returns a token silently for a signed-in user, so that path would then read "could not check").

APPROVED 2026-09-07: the fork owner said offer it (batch 13, tier fix). The ghreason code (`_origin_tracks`, `_git_net_out`) is not on fork main and `origin/ghreason-offer` is gone: build off upstream/main (#947's head `a5191671`). Fork side, `kernel/kernel.py` contention with open fork PRs.
