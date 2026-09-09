---
title: Served labs build vscode-extension/dist once, under a file lock, and copy it under the same lock (setup ERRORs under pytest -n 8)
status: candidate
where: `tests/lab_dist.py` new (DistBuild: flock on dist/.lab-build.lock, an input-keyed marker dist/.lab-built written atomically after the build, copytree ignore for esbuild staging names); `tests/__init__.py` registers the bare name beside romp_load; the thirteen served-lab modules (`tests/test_awaiting_box_sync.py`, `tests/test_dashboard_reload_served.py`, `tests/test_feed_hover_border_static.py`, `tests/test_feed_thread_fold_columns.py`, `tests/test_gear_select_matrix.py`, `tests/test_paste_to_focus_browser.py`, `tests/test_pending_at_tail.py`, `tests/test_pending_bubble_stable.py`, `tests/test_queued_copy_held.py`, `tests/test_scroll_marks_click.py`, `tests/test_scroll_marks_growth.py`, `tests/test_ship_reship.py`, `tests/test_tab_groups_rows.py`) call `lab_dist.copy_dist(dist)` in place of their own esbuild run and copytree; `tests/test_lab_dist.py` new
added: 2026-09-09
pr:
tier: docs
offered:
closed:
---
Under pytest -n 8 two served-lab classes on two workers each ran node esbuild.js into the one dist and copied it; a copy that listed dist during the peer staging phase failed on `.pdf-worker.js.tmp-<pid>-<n>` names renamed away before the copy reached them (shutil.Error at setUpClass; green alone, 11 of 11 iterations red under -n 2 on the two scroll-marks modules). Upstream carries the same thirteen modules unchanged and lacks tests/romp_load.py, so an offer carries the tests/__init__.py registration too.
