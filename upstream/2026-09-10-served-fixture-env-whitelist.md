---
title: Tests: every lab kernel starts from a list of names (kernel_env beside relaunch_env: PATH, HOME, XDG_*, conftest's floor names, the lab's roots and seams) never a copy of the runner's environment, with a private postal bus port that is never started
status: offered
where: tests/test_ship_reship.py (kernel_env, LabKernelEnv), sixteen served test modules' setUpClass
added: 2026-09-10
pr:
tier: docs
offered: their PR #1262
closed:
---
Follow-up to their #1235 (our served-lab env hygiene): the labs still built their own kernel's environment from os.environ, so a live manager's ROMP_MANAGER_PID, ROMP_SERVE_HOST and the machine's postal bus port reached every lab kernel. Tests only; filed from #1235's head (now on main).
