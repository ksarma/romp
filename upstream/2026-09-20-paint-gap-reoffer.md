---
title: Comments panel: the Comment float survives a paint landing in the selectionchange gap, and a drag of selected text ends its press on a source the paint detached
status: candidate
where: ui/webview/file-comments.ts (noteSelectionAtHead, pendingChange, afterPaint, onSelectionChange, openPanel, dragBegan); tests ui/webview/file-comments-paint-gap-browser.test.ts (new), file-comments-paint-offer.test.ts (cases 10 to 12, cutOnPaint), file-comments-keyboard-offer.test.ts (the dispose pin)
added: 2026-09-20
pr:
tier: fix
offered:
closed:
---
Chromium posts selectionchange as a task, 0.7 to 14.3 ms after the keydown over 20 measured presses, and the panel's afterPaint read the live selection at the end of every pass into the record its listener compares with, so a pass landing in that gap (a peer's comment through the poll, a settings pick from another pane) recorded the person's Shift+ArrowRight as the offer's and their own event offered nothing: on a one-line selection the pass leaves intact, the Comment button vanished. Now a pass reads the selection at its head, and a change the float has not answered is a latch the person's event lowers: afterPaint drops the record and leaves the float to that event (a subject the pass left gone or with no box is hidden by the pass as before), and openPanel starts the record afresh. A drag of selected text whose source text node a mid-drag pass detaches had its dragend dispatched at the detached node, out of the document's hearing, and the press flag stood until the next click; the document's capture dragstart now adds a once dragend listener on the source. Client-only; travels with the file-comments candidate (2026-09-07-file-comments-tracked-changes). Two Chromium legs with the real keyboard and mouse and three stand-in cases.
