---
title: A tab-strip section holding the tab being read folds like any other (its header is the hidden tab's stand-in: focus, left/right arrows via `neighborOfFolded`, `aria-current`, an accent-underlined name), and a header click shows the section's SNAPSHOT in the transcript's place: one row per session (emoji, identity color, state pip, a needs-you word that follows the feed's column carried on the ledger as `needsInput`, waiting, flag count, a now line from the current task, else the ledger summary, else the recent top, the working note as its own second line, last-activity age, last message on hover), a click-safe button per row that opens the session and its section; Escape or a second click on the active section's open header returns to the transcript; the model (`ui/webview/tab-snapshot.ts`) is pure and returns the same object when nothing changed; the kernel ledger carries `workingNote` and `needsInput`, both folded into the chat build signature
status: candidate
where: fork branch `tabsnapshot` (`ui/webview/tab-snapshot.ts`, `tab-groups.ts` planStrip/headWords/neighborOfFolded, `render.ts` renderSnapshot/showActive/setActive, `styles.css`, `kernel/kernel.py` build_session ledger, `docs/guide.md`)
added: 2026-09-06
pr:
tier:
offered:
closed:
---
Follows their tab-groups line (our 2026-09-04/06 offers); the header click now also swaps the pane, which they may want as a separate glyph — ask before offering. Phone layout unchanged (flat strip, no sections).

Status detail (migrated from the table): candidate
