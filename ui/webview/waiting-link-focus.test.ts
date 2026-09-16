// RETIRED at the 2026-09-15 upstream pull-in (SWEEP-TRIAGE-2 D2, fixer round 2f); the fold owner removes the file (git rm is
// theirs, not a fixer's). What it pinned: a Waiting-on-you detail link posts its click to the shell and hands the Files pane's
// window the keyboard while that pane is CLOSED, the shell bringing the pane forward. Two upstream changes retire that premise
// together: T317b (https://github.com/romp-on/romp/pull/1391, the shell refuses to bring forward a Files pane whose gear
// control is hidden) and T404 (https://github.com/romp-on/romp/pull/1596, adopted whole: the route follows the OPEN Files pane
// and no setting names a closed one, ui/webview/file-route.ts fileLinkRoute, read in waiting.ts off the shell's panes word).
// Under them a click with the pane closed opens the viewer over the Waiting pane itself, and this file's browser leg (the
// pane toggled off, then shown by the relay) and its executed-body leg (the harness handed the body none of the names the
// route reads) have no live behaviour left to hold. Twin: ui/webview/waiting-pane-browser.test.ts carries the same
// executed openTodoPath body with both arms (the relay with the focus hand-off; the viewer over this pane, nothing posted),
// the hostile-parent and no-iframe cases, the Reply modal's focus-return pin at source, and the browser legs (the hand-off
// with the Files pane on screen; Escape and the modal over the pane). The relayJs() anchor this file sliced from kernel.py,
// the feed's viewFile arm, went with the feed route in the same pull-in.
