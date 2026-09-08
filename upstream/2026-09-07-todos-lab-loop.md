---
title: `tools/romp-lab/todos-lab.sh` and `todos-loop.mjs`: a romp-lab phase that drives the user-todos contract end to end on the real stack (a Haiku session files an ask through `add_user_todo`; Reply, Dismiss, the feed escalation, the gear switch, a kernel restart, the SessionStart context block and the revived session) and cuts the docs GIFs from the recording
status: candidate
where: fork branch `todoslab` (PR pending): `tools/romp-lab/todos-lab.sh`, `tools/romp-lab/todos-loop.mjs`, `tools/romp-lab/README.md`
added: 2026-09-07
pr:
tier: tests-only
offered:
closed:
---
Goes with the user-todos slices (the three 2026-08-22 entries): the loop has nothing to exercise until they land, and it is the capture that produced the user-todos docs GIFs. Tooling only, no kernel or pane change. The lab script is a sibling of `lab.sh`, not a mode in it, because the phase turns the user-todos switch on before boot, runs a postal bus on its own port and scrubs the calling environment harder than the other phases; folding that into `lab.sh` would change the preamble every phase runs.
