---
title: GET /perf names no file path and quotes no judge text
status: candidate
where: kernel/event_model.py (_read_kind, read_bytes_by_kind, checkpoint_stats), kernel/kernel.py (_PerfStats.judge_child_done, _JudgeChild.pass_); tests/test_fold_checkpoints.py test_the_served_read_table_names_holder_kinds_never_paths, tests/test_perf_stats.py test_judge_child_is_served_as_a_size_and_a_status_never_the_line
added: 2026-09-18
pr:
tier: fix
offered:
closed:
---
Two served blocks carried this machines text: checkpoints.readByPath keyed the JSONL readers byte table by absolute path (the home directory, the project directory and the session id in every key), and judge.child stood as the judges childs done line verbatim, whose failures.first is an exception message naming transcript paths. readByPath becomes readByKind (files, bytes and the largest read per holder kind: leaf, agent, states, postal, checkpoint, other), judged from a paths own last segments; judge.child becomes the lines length in characters, a fixed status token (ok, failed), the failure count and the lines per-pass numbers. Both tests fail on the tree before the change with the path and the sid in the served block. Shape changes: the readByPath key is gone; the lines blocks (recordCache, asmCheckpoint, parses, goalIo) no longer ride judge.child. Part of the 2026-09-18 paste-safety review of the snapshot; the second half is perf-served-keys.
