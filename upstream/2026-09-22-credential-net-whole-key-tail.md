---
title: Test-suite credential redaction: every provider-prefix rule takes the whole key, so a key that begins like a provider token is never redacted only up to its first underscore
status: candidate
where: fork branch `quickfix-redaction-prefix-tail`: `tests/credential_patterns.py` (`KEY_FORMATS`, `_REST`, the whole-key rules and the cut-key rule built from one list), `tests/test_env_value_redaction.py` (the two deterministic pins and the property pin read from the pattern source)
added: 2026-09-22
pr:
tier: docs
offered:
closed:
---
Upstream ships the same `tests/credential_patterns.py` (their PR #1005 and its review folds): its `hf_` and `rpa_` rules end at the first `_` or `-` past the twentieth body character, so a key that begins like one of those tokens is redacted only up to that character and the rest stands in the clear in a test report (a CI red on fork PR #862, 2026-09-22: the marker and 60 characters of an 86-character drawn key). The fix appends the rest of the run to every whole-key rule, builds the whole-key and cut-key rules from one list, and pins the property over every prefixed alternative read from the pattern source. Test-only, no runtime change.
