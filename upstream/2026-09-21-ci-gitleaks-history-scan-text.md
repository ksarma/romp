---
title: CI gitleaks history scan reads textual diffs through a committed -diff attribute
status: candidate
where: .github/workflows/ci.yml (the secrets job's history-scan step); tests/gitleaks-config.bats (the committed -diff attribute case); CLAUDE.md (the credentials section's hook bullet, one sentence); tests/gitleaks-require.bats (the ROMP_GITLEAKS_REQUIRE switch and the Run bats env pin); upstream/2026-09-21-ci-gitleaks-history-scan-text.md (this entry)
added: 2026-09-21
pr: 890
tier: fix
offered:
closed:
---
CI's history scan (gitleaks git, which runs git log -p) reads the checkout's .gitattributes, and a path marked -diff prints a Binary files ... differ line with no hunk, so a credential committed in such a path and removed in a later commit was text the scan never saw, while the tree scan (gitleaks dir) reads HEAD, where the file is gone. Reproduced by execution on gitleaks 8.28.0 (CI's pin) and 8.30.1: the configured line exits 0 with no leaks found over a three-commit scratch repository (attribute, credential, removal), the same line with --text reports the finding, redacted, and the tree scan exits 0. The fix adds --text to the --log-opts value, so git prints the textual diff regardless of the attribute. Latent on this repository: the one committed .gitattributes (ui/webview/anchor-map-fixtures/.gitattributes) marks a fixture -text, for its line endings, not -diff, so no commit was hidden from the scan here. The test derives CI's invocation from ci.yml's own run line, so the assertion is that CI's configured scan finds the credential whatever its spelling; red before the fix with the scanner's no leaks found. The pre-push hook is a separate scan (the push, on a developer's machine) and is not changed here.
