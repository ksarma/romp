---
title: A settings pick waits for the session's live subagents and background tasks before it reconnects the CLI; the launched value picked again reconnects nothing
status: candidate
where: kernel/sdk_backend.py: SdkSession._arm_reconnect_if_quiet (called at the request, the ResultMessage settle and a task end; a shell or monitor task's end arms at once, an agent's, a run's or an unknown type's end leaves the arm to the delivery turn's settle), _reset_reconnect_state at the loop top, _note_reconnect_ask, _live_work_counts, _pick_held and snapshot's pickHeld and held-mode fields, _connect_landed (the _launched_effort/_launched_mode/_launched_auth stamps; _options records _launching), the unchanged and already-applying guards in set_effort and set_auth, one log line per setter, _can_use_tool's held-bypass consult, _RECONNECT_CAUSE; kernel/kernel.py: _park_op_locked logs each park, pickHeld through Sessions.live, build_session's status and the reconnecting event, _pick_held_sig; ui/webview/render.ts renderReconnecting's held branch; tests/test_sdk_backend.py SettingsPickWaitsForLiveWork and the LiveSubagentsRetire cause pin, tests/test_kernel_parked_ops_lock.py ParkIsLogged, tests/test_session_auth.py the launching and landing stamps tests, tests/test_kernel_effort_reconnect.py the pickHeld pins, tests/test_injected_voice.py the cause assertion and the key cycle word, ui/webview/effort-switch-pending.test.ts the held pin; docs/reference.md two sentences
added: 2026-09-09
pr:
tier: fix
offered:
closed:
---
Fix tier. Picking effort, permission mode (bypass), fast mode or billing on a session with live subagents, harness background tasks or Workflow runs killed all of them: the reconnect arm read only the open turn (inflight and the untaken hold), never the live sets, and a session idle between its own turns reconnected at once. 26 subagents and 10 background tasks were lost across four sessions on 2026-09-09 to picks that changed nothing. Now a settings-driven reconnect arms only when the live sets are empty, and the exact removal events arm a held one; a rewind keeps its old behaviour. Tests fail before the fix.
