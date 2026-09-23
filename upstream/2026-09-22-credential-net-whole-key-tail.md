---
title: Test-suite credential redaction: every provider-prefix rule takes the whole key, its dotted rest included, so a key that begins like a provider token is never redacted only up to its first underscore or its first dot
status: candidate
where: fork branch `quickfix-redaction-prefix-tail`: `tests/credential_patterns.py` (`KEY_FORMATS`, `_REST` with its dotted rest and dotted cut tail, `_PREFIX_ELLIPSIZED`'s dotted tail, the whole-key rules and the cut-key rule built from one list, the docstring's alphabet paragraph), `tests/test_env_value_redaction.py` (the two deterministic pins, the property pin read from the pattern source with its dotted-rest positions, and the alphabet witness), upstream/2026-09-22-credential-net-whole-key-tail.md (this entry)
added: 2026-09-22
pr:
tier: docs
offered:
closed:
---
Upstream ships the same `tests/credential_patterns.py` (their PR #1005 and its review folds): its `hf_` and `rpa_` rules end at the first `_` or `-` past the twentieth body character, so a key that begins like one of those tokens is redacted only up to that character and the rest stands in the clear in a test report (a CI red on fork PR #862, 2026-09-22: the marker and 60 characters of an 86-character drawn key). The fix appends the rest of the run to every whole-key rule, builds the whole-key and cut-key rules from one list, and pins the property over every prefixed alternative read from the pattern source. Round 1 of the fork's review found a second closure beside it, reproduced on upstream main as well: a prefixed key with `.<signature>` after its run was the marker and `.<signature>` in a value position, bare, alone on a line and against a cut, while the same token without a prefix was taken whole by the generic rule, which loses to a whole-key rule at a shared start. `_REST` now carries the dotted rest and the dotted cut tail and the cut-key rule's tail the dotted rest, the shape the JWT rules already had, with a per-position pin over the same population; the module docstring names the alphabet (base64url) and its limit, with one witness pin. Test-only, no runtime change.
