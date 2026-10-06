---
title: The mail-box strokes lab copies its screenshots into its own state root's drops directory, not the live state root's
status: candidate
where: tests/test_mail_box_strokes_served.py (module docstring; DROPS removed; setUpClass's drops directory and the screenshot copy), upstream/2026-10-03-tests-mailbox-drops-lab-root.md (this entry)
added: 2026-10-03
pr:
tier: docs
offered:
closed:
---
The project's copy of tests/test_mail_box_strokes_served.py (their PR #1921) copies the four screenshots it takes (mailbox-after-{dark,light}-{shot,clip}.png) into `~/.local/state/romp/drops`. The path is built from the home directory alone, so every run that reaches its screenshots writes into the live state root of whoever runs the suite, whatever ROMP_STATE_DIR or XDG_STATE_HOME the run sets, and the files stay there after the lab is removed. The module's own docstring promises a hermetic kernel, never the live one, yet this copy writes into the live state root. The fork's copy removes the DROPS constant and copies the same four files into the lab kernel's own state root (`<lab>/xdg/romp/drops`), which tearDownClass removes with the rest of the lab, and the module docstring says where the pictures go. What it gives up: the constant's comment named that directory as the place a manager or a verifier reads pictures from, and after a run the pictures are gone with the lab. The assertion (the outgoing box's border-left is not the recipient's magenta) is unchanged. Tests only, so docs tier.

Found in the fork's fold of the project's main through their PR #1961 (upstream fold 4); re-checked at upstream/main, whose copy still writes there. The fork's copy also takes its bundles and its kernel's port through tests/lab_dist.py and tests/lab_ports.py, which are fork-only helpers; an offer carries the drops change alone, on the project's tests.dist_copy shape.
