---
title: test_login_records' hung token command case ends the sleep its shell forks, which run_helper's timeout leaves running
status: candidate
where: tests/test_login_records.py (TheTokenCommand.test_a_hung_command_is_cut_by_the_bound: the token command records the pid of the sleep it forks, and the test ends that pid in cleanup); upstream/2026-10-06-tests-login-hung-command-child.md (this entry)
added: 2026-10-06
pr: 984
tier: docs
offered:
closed:
---
The case's token command, `sleep 30`, outlived the test: dash, the /bin/sh of Debian and Ubuntu, forks it, and run_helper's timeout kills only the shell it started, so the sleep ran on for about 29 s with the run's temp root in its environment. On the fork the run-end process check in tests/conftest.py then failed any run of the module that ended while it slept, with all 61 tests passing. The command now backgrounds the sleep, records its pid and waits; the test ends that pid in cleanup. The case still makes the bound return while a child of the shell holds the stdout pipe, and backgrounding gives it that shape under every shell (bash runs a lone command in its own place, so there the kill ended the hang itself). Tests only, so docs tier.

upstream/main (fetched 2026-10-06) carries the same case line for line, the same `_read` helper and the same subprocess call in run_helper; its kernel/credentials.py, loaded on its own and given the case's command with a 1 s bound, left the same sleep running after the call returned. Its tests/conftest.py has no run-end process check, so there the stray sleep fails nothing: it ends about 29 s after the test.
