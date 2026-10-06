---
title: A row the CLI writes for input it is not running opens no turn: the session host and the kernel counted a model switch's echo (a user row flagged isReplay, carrying <local-command-stdout>, written outside any turn with no result after it) as a turn the CLI opened, and the session read Working for good
status: candidate
where: kernel/session_host.py (LOCAL_COMMAND_TAGS, _cli_echo, SessionHost._track), kernel/sdk_backend.py (LOCAL_COMMAND_TAGS, _is_local_command_echo, SdkSession._turn_frame), tests/fixtures/fake_claude.py (a set_model that changes the model is echoed before its answer), tests/test_session_host.py (ECHO_ROWS, TURN_ROWS, ReplayedEchoes, HostProcess test_a_model_switchs_echo_after_a_result_leaves_no_open_turn_for_the_next_attach and test_an_unattached_cli_whose_last_row_is_a_model_switchs_echo_is_ended_after_the_grace), tests/test_queued_sends_not_fused.py (test_a_local_command_echo_counts_no_turn_and_releases_no_hold), upstream/2026-10-06-host-replayed-echo-opens-no-turn.md (this entry)
added: 2026-10-06
pr:
tier: fix
offered:
closed:
---
A model switch asked for after a turn makes the CLI write the /model confirmation to stdout as a user row flagged isReplay, before its control_response, outside any turn, and no result follows it. The host re-opened its turn count on any assistant or user row arriving at zero, so the count stayed at one: every attaching kernel was told a turn was open, the unattached grace never ended the CLI, and a re-exec waited for a result. The kernel made the same count on its own (_turn_frame took every main-conversation UserMessage). The population is what the CLI marks: the isReplay key, which its own turn-evidence test skips whatever the value, plus its recogniser of local-command output (either tag anywhere in the text). The host tests both; the kernel tests the tags, because the SDK drops the key when it parses a row. Assistant rows and the CLI's own user rows still re-open the count.
