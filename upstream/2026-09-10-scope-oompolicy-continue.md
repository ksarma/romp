---
title: Name an OOM-killed scope in the crash heal's log line and resume notice
status: candidate
where: kernel/sdk_backend.py (_heal_cut_session, _oom_killed_scope, scope_results, oom_killed_scope, CRASH_RESUME_NUDGE_OOM, is_crash_resume_nudge); tests/test_sdk_lifecycle_hardening.py CrashHeal
added: 2026-09-10
pr: 580
tier: fix
offered:
closed:
---
The offerable half of fork PR scope-oompolicy-continue. When a session's CLI dies mid-turn, the heal asks systemctl --user show over the session's own romp-session-<sid8>-*.scope pattern and, on Result=oom-kill, says so in the kernel log and queues an out-of-memory form of the crash resume notice instead of the bare one, so a whole-scope stop over one OOM-killed tool child is named rather than read as an unexplained exit 143. The other half, OOMPolicy=continue on every scope in bin/romp-cli-scope, is fork-only (the scope wrapper: fork PR 244; offers 307 and 333 closed).
