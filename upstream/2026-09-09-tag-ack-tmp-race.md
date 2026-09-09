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
The judge is one module object per process, so jd.STATE is shared across every module an xdist worker collected; a neighbour fixture that rebinds it to a temp dir it removes without restoring the prior root left any tag-edit ack test whose first touch of the views file is a direct write_text failing with FileNotFoundError on timeline-views.json when it ran first on a worker after that fixture. Verified on the base, polluter first, one class at a time: LegacyStoreStampedOnce, LegacyTagsStampedOnFirstRead, MigrationStampsTheArchivedTag, ReaderRestampKeepsTheDiskCap and ReaderRestampUnwritableNamesTheDrop fail as classes, ReaderRestampUnwritable when its read-only test runs first; the other 18 classes pass. Each test now makes, binds, restores and removes its own state root, which covers every class whichever test runs first; a regression class (OwnStateRoot) simulates the polluter inside the module; the in-test mkdtemp dirs are removed by the test that made them.
