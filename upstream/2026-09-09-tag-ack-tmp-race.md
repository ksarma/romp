---
title: Tests: the tag-edit ack module runs every test under a state root of its own
status: merged
where: tests/test_tag_edit_ack.py
added: 2026-09-09
pr:
tier: docs
offered: their PR #1221 (the slim hygiene variant)
closed: 2026-09-10
---
The judge is one module object per process, so jd.STATE is shared across every module an xdist worker collected; a neighbour fixture that rebinds it to a temp dir it removes without restoring the prior root left any tag-edit ack test whose first touch of the views file is a direct write_text failing with FileNotFoundError on timeline-views.json when it ran first on a worker after that fixture. Verified on the base, polluter first, one class at a time: LegacyStoreStampedOnce, LegacyTagsStampedOnFirstRead, MigrationStampsTheArchivedTag, ReaderRestampKeepsTheDiskCap and ReaderRestampUnwritableNamesTheDrop fail as classes, ReaderRestampUnwritable when its read-only test runs first; the other 18 classes pass. Each test now makes, binds, restores and removes its own state root, which covers every class whichever test runs first; a regression class (OwnStateRoot) simulates the polluter inside the module; the in-test mkdtemp dirs are removed by the test that made them. OwnStateRoot also walks every TestCase subclass in the module's namespace (what pytest collects from it), runs each class's setUp on a fresh instance and fails by name any class that leaves jd.STATE off a new root, so the invariant is enforced by execution across every class, not pinned in two hand-listed setUps.

2026-09-09: offered upstream as the slim hygiene variant only (the _own_state helper, the two setUps, the three global restores, the three rmtree cleanups, WebBootWiring as a _Wire and one direct-write regression test; about 75 lines), on the user's ruling. The roster walk, the pytest-shape guard and the second OwnStateRoot test stay fork-only and retire when the fold carries their #1176's ba878a98, which fixed the failure's cause.
