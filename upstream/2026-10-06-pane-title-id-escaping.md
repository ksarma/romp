---
title: Escape a pane title and id for every served context: the shim bakes LABEL (the title) and APP (the id) as JavaScript string literals via json.dumps, and the id rule matches the whole string
status: candidate
where: kernel/kernel.py (_shim bakes APP and LABEL with json.dumps(ensure_ascii=True) into bare slots, as LOADEDPV bakes pvv; _PANE_ID_RE anchors with \Z so _pane_check refuses an id ending in a newline at all three install roads, POST /pane and the CLI door through define_pane, and the disk re-check _panes_snapshot runs); tests/test_pane_registry.py (the behavioural shim, id-rule and sink-census pins); ui/webview/pane-shim-stale.test.ts (the shim template the webview leg lifts)
added: 2026-10-06
pr:
tier: fix
offered:
closed:
---
A pane title is free text (only length and non-empty are checked), so a title holding a quote, a backslash or a newline reached the shim served at /pane/<id>/shim.js unescaped: it was baked into a double-quoted JavaScript string literal (var LABEL="%s"), so the quote broke the string and the backslash or newline made the served shim a SyntaxError that never ran. The fix bakes LABEL and APP with json.dumps so the shim parses and LABEL equals the title for any title. Separately, _PANE_ID_RE was applied with re.match and a $ anchor, which matches before a terminal newline, so an id ending in a newline passed the rule and reached the landing unquoted markup and CSS; the rule now anchors with \Z (the whole string). The other title sinks (the rail, the phone tab, the body attribute) already escape through _html_esc, and the WS-drop bell row renders client-side through textContent; the id is inert in its remaining sinks once it is regex-confined. Defence in depth, offered as a correctness fix.
