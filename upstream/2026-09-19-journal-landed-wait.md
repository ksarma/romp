---
title: The journal-fault host test waits for the record to land before reading the journal
status: candidate
where: tests/test_session_host.py
added: 2026-09-19
pr:
tier: docs
offered:
closed:
---
tests/test_session_host.py's journal-fault test (test_a_journal_write_fault_is_a_fault_frame_not_the_clis_death) read the journal directory the instant the kernel side received the turn's result frame and asserted it held every record but the faulted one. The host sends a record's `out` frame one event-loop turn before its writer task appends the record: publication precedes durability by design (the module docstring of kernel/session_host.py, and the host section of docs/reference.md), so a frame on the socket promises nothing about the disk yet. A loaded full-suite run on the fork read [0] where [0, 2] landed a moment later (PR 787's sweep on ccd8d8fe9, base 1d6268823: 1 failed of 17172 passed); with the writer's delay seam at 0.05 s the first read is [0] and a re-read is [0, 2], 3 of 3 runs. The fix is the module's own precedent (4ec6da845, the turn test and the lagging-writer test): the read waits on _journal_landed for every live offset but the faulted one (readers skip the gap marker, so the count is theirs), and the test carries _test_journal_delay_s=0.05 so the late landing is certain instead of a matter of scheduling. Tests only; no product change. Upstream's copy of the test is byte-identical and unwaited: checked at upstream/main ea3c82725 (2026-09-18), whose last three commits on the file are 280b73cc9, 340262f7e and 4ec6da845, and _journal_landed is called there only from the two siblings. Open upstream PR 1849 (head a569e216e) keeps _read_cli's send-then-append order (its hunks touch neither the queue put nor the `out` send) and adds another unwaited read of the journal at a result frame, in its re-exec test (the assertion that the journal's last four records are assistant, result, assistant, result).
