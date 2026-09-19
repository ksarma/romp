---
title: Tests: the routing sweep in tests/test_perf_stats.py reads every text file git tracks or would track and a plant test proves its file set is derived, not listed; PushStages' docstring states the foreign push case as ownership (a thread never registered as an owner) and the openness wording joins the retired table; the sweep's docstring records what its file count counts and the command that reproduces it
status: candidate
where: tests/test_perf_stats.py (RoutingStatements, PushStages' docstring, RETIRED_WORDINGS; from git diff --name-only against PR 797's head)
added: 2026-09-19
pr: 831
tier: docs
offered:
closed:
---
Three items from the closing check of fork PR 797 (the stage-attribution fix), all tests and docstrings. The sweep's old eight-directory walk omitted the root files, plans/, claude/, hooks/, vscode-extension/ and ui/ outside ui/webview, none of which named a routed block, so it was complete by luck; the scan now lists the tree with git ls-files (cached plus untracked, ignores honoured), skips symlinks and reads a file as text when its first 8 KiB hold no NUL byte and it decodes as UTF-8, measured at 0.64 s for the whole tree against 0.59 s before. The plant test writes a file in plans/ naming a routed block with a retired wording, asserts both pins red, removes it in a finally and asserts both green; the scan holds a shared flock and the plant an exclusive one on a lock file in the worktree's git dir, so every process over that checkout waits on it, xdist workers and separate runs with their own TMPDIR alike. The docstring sentence that said a bare _push is foreign when no cycle is open was false under a literal reading, since ownership is a registration cycle() leaves standing; it now says a thread that opened no cycle and so was never registered as an owner, and the old phrase is refused by the sweep from here. The count of places stating the rule appears nowhere in the tree; the pin's docstring now defines it as the size of the swept file set, one entry per text file matching the block regex at least once, with the reproducing command, and holds no count of statements.
