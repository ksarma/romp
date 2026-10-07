---
title: The dashboard shell builds custom panes from GET /panes, one source for the pane records
status: approved
where: kernel/kernel.py (_landing, _PANE_ID_RE, _PANE_URL_RE (new), _pane_check, _pane_source_kind, the GET /panes handler, the shell's head script, _LANDING_PANE_RECORDS_JS (new), _PANES_ADOPT_JS (new), _LANDING_ERRS_JS, _LANDING_JS, _LANDING_FOCUS_JS, _LANDING_MOBILE_JS, _LANDING_COLLAPSE_JS, _LANDING_BOOT_JS, _RELOAD_CORE_JS, _reload_core, _stale_block, _shim, _panes_snapshot, _panes_rev, _panes_attr, _data_pane_markup); ui/webview/gear.js; ui/webview/palette-main.ts; ui/webview/panedock-main.ts; ui/webview/settings.ts; ui/webview/gear-pane-records.test.ts (new); ui/webview/gear-tabs.test.ts; ui/webview/palette-main-pane-records.test.ts (new); ui/webview/panedock-main-pane-records.test.ts (new); ui/webview/settings.test.ts; tests/__init__.py; tests/pane_records_stub.py (new); tests/test_artifacts_list.py; tests/test_error_center.py; tests/test_files_pane.py; tests/test_hermetic_kernel_postal.py; tests/test_kernel_auth_hardening.py; tests/test_kernel_boot_splash.py; tests/test_kernel_mobile.py; tests/test_kernel_pane_rail.py; tests/test_kernel_update.py; tests/test_pane_order_parity.py; tests/test_pane_id_keyed_lookups.py (new); tests/test_pane_records_one_source.py (new); tests/test_pane_registry.py; tests/test_pane_registry_served.py; tests/test_pane_set_revision_read.py (new); tests/test_pane_state_broadcast.py; tests/test_shell_reads_check_status.py; tests/test_waiting_pane.py; upstream/2026-10-06-shell-panes-from-get-panes.md (this entry)
added: 2026-10-06
pr: 989
tier: fix
offered:
closed:
---
The dashboard shell builds its custom panes in the browser from GET /panes, the records romp pane list reads, instead of from markup rendered into the page, and every page takes the pane-set revision from GET /panes: one source for the pane records. GET /panes answers its rows and its revision from one listing; it took two, so a pane defined between them made the two disagree. The project's main (f4a572008, read only) renders custom panes into the shell the same way and has the same two-listing handler; the kernel lines this change removes are byte-identical there except the reload core's member list, which the fork extends. The census test walks the fork's page route table, so an offer needs a test of another shape; the lines this change removes from ui/webview's three files are in the project's files, and the gear's press handling uses pressHold from ui/webview/actions.ts, which the project's actions.ts lacks.
The kernel now checks a pane's URL and route sources whole, as it checks the id, and the URL pattern lists by hand
every character that Python's or JavaScript's whitespace class matches, so the shell's check and Python's agree on
every record GET /panes serves. A pane file an earlier kernel wrote that the stricter check refuses (an id or a source
ending in a newline, a URL holding U+FEFF) is skipped when the kernel reads the directory, and stderr names the file
by its path and says to delete it by hand: romp pane remove reaches only the listed panes and is not widened, since
the id joins a path.
Every object the shell's and the phone's scripts look a pane id up in now has no prototype, so a pane whose id is an
Object member's name (constructor) reads only what was set under it; tests/test_pane_id_keyed_lookups.py holds each
such lookup to that. The gear and the settings reader, which copy the stored pane set, test only its own keys, so
such a pane's gear choice survives a save of another setting and the palette reads it. While the read of GET /panes is
not in, the docking kit stores no layout (a late answer starts it again from the stored one), the gear says so in a
visible status line, and the palette lists the defined panes after every command its boot registers and clears its
cached key map when they arrive.
