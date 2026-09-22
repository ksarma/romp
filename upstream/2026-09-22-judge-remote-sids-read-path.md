---
title: The judge's dead-session ladder reads the remote-sids mirror where the postal bus writes it (STATE/postal/remote-sids); rule 5 had read a path nothing wrote since its birth and never fired
status: candidate
where: kernel/judge.py (_presumed_closed), postal/postal_service.py (_write_remote_sids docstring), tests/test_dead_session_staleness.py (ReaderFollowsTheWriter), tests/test_judge_propagate_loads.py
added: 2026-09-22
pr:
tier: fix
offered:
closed:
---
Upstream carries the same two bindings (the judge's STATE is the romp root, the bus's is the root plus postal) and the same read in _presumed_closed, so rule 5 of its dead-session ladder is dead there too: every sid reaching it answers cannot-determine, and a dead sender's card settles only by rules 1 to 3. Found as a side finding of the fork's postal-bus tests PR (fork PR #894), where the reviewer's ruling asked for both STATE bindings to be read and the read to be run; the probe there confirmed it by execution and filed it for its own fix-tier PR. The reader moves to the writer's path; one test runs the real writer and the real reader over one root under both root shapes. Fix tier: product code with a test red before it.
