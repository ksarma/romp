---
title: bats decides every bare negation of the tree: the line scanner is replaced by an oracle that rewrites each candidate to `! true` and `! false` and runs its test under bats
status: candidate
where: tests/test_bats_bare_negation.py (the module rewritten: bash_test_extents, candidates, negated_pipeline, rewrite, decide, decide_under_bats, run_test_alone, _run_bats, the register ground_truth_shapes with RECORDED, BatsSuites, BatsCorpus, BatsGroundTruth, BatsRoad), tests/bats-bare-negation-shell-job.bats (new: the wrapper CI shell job runs the bats-backed classes through), tests/test_ci_bats_bound.py (run_bats_step, the one reading of the Run bats step, imported by the module), tests/test_lab_dist.py (_TREE_COPIERS allowlists the module copy of the tree)
added: 2026-09-20
pr: 871
tier: docs
offered:
closed:
---
The module ships upstream: its first version (a line scanner over bats tests) was offered and merged there, and this rewrite replaces that scanner whole. bats is the oracle: for every `!` word in command text of a test (bash -n decides what is command text and where a test closes) the negated pipeline is rewritten to `! true` and to `! false`, the test runs alone under each, twice, and a differing pair whose sides agree is a read status, both passing an inert negation (a defect), everything else undecided and reported. A register of synthetic shapes (its count and the measured figures are in the module docstring) records what bats says under both rewrites (verified under bats 1.10.0 and 1.11.1) and gates recall, the extent of the negated pipeline (here-documents it introduces, pipelines continued past a comment, operators inside a construct bash reads whole, negated compounds, glued comments, ANSI-C quotes, a close sharing the last command line, introducing a here-document or followed by file-scope text on its line or running on to later lines) and the decision rule; the module's tests skip under a bash lacking what it reads (macOS's 3.2.57), naming it. CI shell job runs the register, the road and the corpus through a bats wrapper. Fork PR #871.
