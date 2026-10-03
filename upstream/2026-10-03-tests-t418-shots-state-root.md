---
title: The tool-rows browser test (T418) saves its screenshots only when asked, under the run's own state root, never under the home directory
status: candidate
where: tests/test_tool_rows_vocab_browser.py (_drops_dir, new; _result reads it; the module docstring); tests/test_tool_rows_vocab_shots_root.py (new); upstream/2026-10-03-tests-t418-shots-state-root.md (this entry)
added: 2026-10-03
pr: 962
tier: docs
offered:
closed:
---
tests/test_tool_rows_vocab_browser.py saved six screenshots by default to a drops folder built from the home directory (~/.local/state/romp/drops) whenever that folder's parent existed, so on a machine running romp every run that reached the browser, a full test run included, wrote into that machine's live state root. The shots are now opt-in (T418_SHOTS=1) and go to drops/ under the run's own state root, ROMP_STATE_DIR, else <XDG_STATE_HOME>/romp (lab_ports.state_root), read when the shots are taken; a run that asks for shots and names neither variable fails instead of building a path from the home directory. The module docstring says where the shots go and how to turn them on; every assertion of the browser test is unchanged. tests/test_tool_rows_vocab_shots_root.py pins it by execution with no browser: it loads the module under a private name with HOME at a temp home that holds a romp state root and the two state-root names in a separate temp tree, runs the real _result with only the driver stubbed, and asserts the shots land in drops/ under the state root (ROMP_STATE_DIR first, then the XDG root), the switch and the root are read when _result runs rather than when the module loads, nothing appears under the home, nothing is written with the switch off or set to anything but 1, and a run with no root named fails; against the old module it reds on files under the temp home. The driver's own screenshot path is held by a read of DRIVER's source, not an execution: no CI test runs the driver with shots on. Tests only, so docs tier.

The fix reads the state root through tests/lab_ports.py (state_root), which the fork added in the candidate upstream/2026-10-02-tests-served-lab-ports.md; the project's main as of 2026-10-03 has the same DROPS line and gate and no tests/lab_ports.py, so an offer ahead of that one reads the two names inline.
