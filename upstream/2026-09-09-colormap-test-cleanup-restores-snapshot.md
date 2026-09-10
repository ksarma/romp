---
title: tests/test_colormap_aurora.py restores the colormap it found instead of writing hawaii, so a serial run no longer hands later modules a foreign default palette
status: candidate
where: tests/test_colormap_aurora.py (the cleanup snapshots STATE/colormap and puts it back, resetting _cmap_cache); tests/test_feed_delta.py (_DefaultPalette base class)
added: 2026-09-09
pr:
tier: docs
offered:
closed:
---
The aurora test's finally wrote hawaii into the judge STATE every kernel-loading test shares (since the commit that added it); a fold's conftest change stopped a neighbouring module from masking the file and seven feed-delta tints read hawaii on CI's serial run. Upstream carries the identical finally. Landed in the 2026-09-09 fold (slice 3).
