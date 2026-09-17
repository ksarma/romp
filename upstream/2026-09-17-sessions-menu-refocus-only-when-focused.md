---
title: The Sessions pane's row menu refocuses the row's head on every close, the window's blur included, so a click into another pane pulls the keyboard back into the pane
status: candidate
where: ui/webview/fleet.ts (showSessionMenu: the onClose returns early when document.hasFocus() is false, else focuses the head by sid with preventScroll); ui/webview/sessions-menu.test.ts (the re-pinned source pin; two browser legs over the real bundle in the shell's frame arrangement: Chromium pins the residue, Firefox the composer losing the keyboard)
added: 2026-09-17
pr:
tier: fix
offered:
closed:
---
Upstream's fleet.ts at f4daa02e2 (the menu landed in 2d7f4c0ed with no onClose; the return to the head, this entry's line, came in its review round two, 971a42a30; both through upstream's PR https://github.com/romp-on/romp/pull/1782) closes the row menu on the window's blur and then runs the caller's onClose, which focuses the head unconditionally: with the chat and Sessions panes as sibling iframes, a right-click on a row followed by a click into the chat composer without picking closes the menu through the blur and refocuses the head. In Firefox the composer loses the keyboard and the next letters land on the head, where Space or Enter opens that session; in Chromium and the VS Code webview a frame-focus re-entrancy guard keeps the composer, and the residue is a stale activeElement (the head) in the unfocused pane. The fix guards the return as the shared builder's own return already does (return when the document has lost the focus; else focus the head with preventScroll), and keeps onClose: after a push rebuilds the list under the open menu the opener is detached, the builder's return does nothing, and the sid-keyed onClose is what lands Escape on the new head. Fails before: the Chromium leg reads the head as the pane's activeElement after the blur close, and the Firefox leg reads the chat frame's body where the composer should be. No offer under the no-new-upstreaming word; the ledger is the queue.
