---
title: Kernel Python follows the SDK venv: the interpreter pick, the ABI check, and the manager's audit rows for an unrequested SIGTERM
status: resolved-upstream
where: fork PR #272 (py314, merged 2026-09-07): `bin/romp-serve` pick_python (venv-first, tag-gated venv join, one venv verdict), `kernel/kernel.py` (the ABI check; the manager's auditSigterm rows), tests under `tests/` and `tests/*.bats`; docs/reference.md and docs/install.md text (audit row 45)
added: 2026-09-09
pr:
tier: fix
offered:
closed: 2026-09-18
---
Created on the user's ruling of 2026-09-09 (offer): the py314 work had no ledger entry. It is offered through the features plan's two row-27 PRs, kernel-python-follows-venv (fix, docs row 45 riding) and unrequested-sigterm-audit (fix); the bats state-root ratchet (audit row 11) and the empty-XDG readers (row 19, their PR #1211) were the same fork PR's other pieces and travel separately. The 2026-09-06 outage (romp-serve picking the newest python after uv installed one into ~/.local/bin, the 3.12 SDK venv failing to import under it) is the case.

2026-09-18: resolved upstream, not filed. Both halves merged there on 2026-09-10: https://github.com/romp-on/romp/pull/1282 (merge da09081132a, the kernel Python follows the SDK venv) and https://github.com/romp-on/romp/pull/1286 (merge f0597caa1a, the unrequested-SIGTERM audit rows), with the follow-up https://github.com/romp-on/romp/pull/1299 (merge b26c895327). bin/romp-serve, bin/romp-sdk-setup and bin/romp-codex-setup are byte-identical between the two tips and auditSigterm is in the project's bin/romp-manager. The fork PR was #272.
