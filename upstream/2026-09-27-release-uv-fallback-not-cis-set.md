---
title: release.sh's uv fallback no longer calls pytest and cryptography CI's dependency set
status: candidate
where: scripts/release.sh (the uv fallback's comment and its say line; the text offered); tests/release-sh.bats (the resolver comment, and the case that reads the say line against the uvx argv and ci.yml's Python-job install set; the text offered); .github/workflows/ci.yml (the Run pytest step's comment on the session-end thread guard; fork-only); tests/conftest.py (the session-end thread guard; fork-only); tests/test_session_end_thread_guard.py (the guard's pins; fork-only); tests/test_bats_bare_negation.py (the docstring's list of the Python cells' installs, now with pytest-xdist; fork-only); upstream/2026-09-27-release-uv-fallback-not-cis-set.md (this entry)
added: 2026-09-27
pr: 922
tier: docs
offered:
closed:
---
Upstream still calls its uv fallback CI's set. At upstream/main f4a572008 the comment at scripts/release.sh:333 and the one at tests/release-sh.bats:460 say "CI's exact dep set", and the say line at scripts/release.sh:341 prints "CI's dep set", for pytest and cryptography, while upstream's ci.yml:107 installs pytest, pytest-timeout and cryptography. The text became false at f40145063 (2026-09-03), which added pytest-timeout to ci.yml, before the fork's #917. The fork's texts now name the two packages and say what the fallback leaves out, and a bats case reads the say line against the uvx argv and ci.yml's Python-job install set, so it fails on the old line. Upstream installs no pytest-xdist, so the fork's wording does not carry over verbatim: upstream's correction names pytest-timeout only. Comment and message text plus one test; the uv command is unchanged.
