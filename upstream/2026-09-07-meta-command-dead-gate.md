---
title: `_route_meta_command` evaluates `_ops_gate(sid)` once per `/model`, `/effort` or `/fast` and never reads it: upstream's #923 merge reintroduced the line the #954 review had removed, so every meta command pays a tmux fork, a discover sweep and a usage read for a value nothing reads (ruff F841), and its comment says the value is read
status: candidate
where: `kernel/kernel.py` `_route_meta_command`: the fork dropped the assignment and reworded the docstring in the 2026-09-07 fold; upstream/main still carries it. The setters' own verdicts, which `state` reads, are pinned by `tests/test_kernel_parked_ops_lock.py`
added: 2026-09-07
pr:
tier: fix
offered:
closed:
---
Found by the fold's review (2026-09-07): the only new F-class finding against the fork. No behaviour change; one redundant expensive gate per meta command on the handler thread.
