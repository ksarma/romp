---
title: The working-notes read-once pin counts only the notes directory reads
status: approved
where: tests/test_pusher_change_gates.py WorkingNotesMemo.test_read_once_per_directory_version
added: 2026-09-17
pr:
tier: docs
offered:
closed:
---
The read-once pin on the working notes counted every Path.read_text call in the process, so a read by a thread another test module left running in the same xdist worker failed it once; it now counts only reads of files under km.WORKING_DIR. The module ships upstream unchanged (byte-identical at the fork's stage 1 tip f4daa02e2 and at fork main 870797588). WorkingNotesMemo.test_read_once_per_directory_version patches Path.read_text on the CLASS with mock.patch.object and asserts one read for two _working_notes() calls; the patch is process-global (pathlib.Path is one class per process, whichever kernel copy a module loaded), and the suite leaves kernel and backend threads alive across modules with no reaping (a single-process run found 14 alive at one point: acceptors, websocket senders, sdk lanes), so under xdist a peer module's thread can read_text some other file inside the spy's window. The fork's 2026-09-17 sweep (-n 4) counted 2 where 1 was expected (AssertionError: 2 != 1 at the count line) while the module was green alone three of three, and _working_notes itself is unchanged on both trees. The hardening is the repo's own idiom for this spy (tests/test_cleared_set_memo.py appends only p == self.path; tests/test_file_read_memos.py only its two files): a counting function that appends a read only when Path(p).parent == km.WORKING_DIR, the same assertions, and the count assertion carrying the reads list as its message so a future red names the path read twice instead of a bare count. The failure is a race between test modules and not reproducible on demand; the module is green twice by the venv recipe (13 passed). Tests only, so tier docs; filed by the fork's 2026-09-17 catch-up fold (fixer round c3); the offer waits on the no-new-upstreaming hold like the 2026-09-16 entries.

2026-09-18: approved for offer by the user (batch 7 of the 2026-09-18 plan; his answer covers the fix and docs entries of batches 2 to 7, batch by batch, features excluded).
