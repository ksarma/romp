---
title: Tests: the tag-edit ack module runs every test under a state root of its own
status: candidate
where: tests/test_tag_edit_ack.py
added: 2026-09-09
pr:
tier: docs
offered:
closed:
---
The judge is one module object per process, so jd.STATE is shared across every module an xdist worker collected; a neighbour fixture that rebinds it to a temp dir it removes without restoring the prior root left the tag-edit ack classes that write the views file directly failing with FileNotFoundError on timeline-views.json. Each test now makes, binds, restores and removes its own state root, and the in-test mkdtemp dirs are removed by the test that made them.
