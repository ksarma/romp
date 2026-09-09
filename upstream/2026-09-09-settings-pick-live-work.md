---
title: A settings pick waits for the session's live subagents and background tasks before it reconnects the CLI; the launched value picked again reconnects nothing
status: candidate
where: kernel/sdk_backend.py: SdkSession._arm_reconnect_if_quiet (called at the request, the ResultMessage settle, the SubagentStop hook, a task end and a run end), _note_reconnect_ask, the _launched_effort/_launched_mode/_launched_fast/_launched_auth stamps in _options, the unchanged guards in set_effort and set_auth, one log line per setter, _RECONNECT_CAUSE; kernel/kernel.py: _park_op_locked logs each park; tests/test_sdk_backend.py SettingsPickWaitsForLiveWork, tests/test_kernel_parked_ops_lock.py ParkIsLogged, tests/test_session_auth.py the stamps test; docs/reference.md one sentence
added: 2026-09-09
pr:
tier: fix
offered:
closed:
---
Fix tier. Picking effort, permission mode (bypass), fast mode or billing on a session with live subagents, harness background tasks or Workflow runs killed all of them: the reconnect arm read only the open turn (inflight and the untaken hold), never the live sets, and a session idle between its own turns reconnected at once. 26 subagents and 10 background tasks were lost across four sessions on 2026-09-09 to picks that changed nothing. Now a settings-driven reconnect arms only when the live sets are empty, and the exact removal events arm a held one; a rewind keeps its old behaviour. Tests fail before the fix.
