---
title: `romp keyswap <name>` is refused on this fork in FILE mode only. Upstream's swap (their `b4ca13e7` / `d177a8a8` / `60051794`, 2026-09-04) rewrites the `ANTHROPIC_API_KEY=` line of `service.env` from a sibling `service.env.<name>`, which presumes API keys in files; this fork does not write API keys to files, so with no `ROMP_CREDENTIAL_COMMAND` the named form exits 2 with one fixed message, reads and writes nothing, and has no flag that lets it through. In command mode the same argument writes the selector file (a name, never a key): see the key-free row below. The boot warning for a credential-shaped line in the env file under a declared `ROMP_EXPECTED_AUTH` (`_warn_credential_lines_in_env_file`) stays on this row and speaks in file mode; in command mode the key-free row's `key_source_verdict` covers the same file (the line is ignored there, the command wins) and this warning is skipped, so one line is said about that file, never two that disagree
status: divergence
where: `cli/keyswap.py` (`REFUSAL`, the file-mode branch of `main`, `_candidates`, and in `_cycle` the second and third lines of the no-kernel and no-route blocks, which upstream's end with `The file is already swapped`), `bin/romp` (help row), `docs/reference.md` (the keyswap section's file-mode paragraph); tests in `tests/test_keyswap_refusal.py` (`NamedSwapRefused`), the adapted `tests/test_keyswap.py` and `tests/romp.bats`
added: 2026-09-05
pr:
tier:
offered:
closed:
---
Fold upfold0905 (2026-09-05); narrowed to file mode 2026-09-05 when the key-free mode landed. Not for offering: the refusal encodes the fork's policy. `kernel/keysource.py` is carried unchanged (its `write_key` is no longer called by anything here); the kernel's live read of a `service.env` key line stays for installations that keep one there.

Status detail (migrated from the table): divergence
