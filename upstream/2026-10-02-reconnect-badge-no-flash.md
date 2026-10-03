---
title: The corner reconnecting badge waits one second before it paints, so a reconnect that lands sooner shows no flash
status: candidate
where: kernel/kernel.py (_RECONN_BADGE_HOLD_MS, new; _pane_spin's badge listeners); tests/test_pane_loader_reconnect.py (ReconnectBadgeHold, new; the spin harness's document); upstream/2026-10-02-reconnect-badge-no-flash.md (this entry)
added: 2026-10-02
pr: 950
tier: feature
offered:
closed:
---
The badge that says reconnecting over a pane with content (T217) paints on every socket drop and comes down at the pane's first fresh frame, so a reconnect that lands in a few hundred milliseconds flashes it: in a hermetic lab on the fork, 386 ms on a phone-sized return and 620 ms on a desktop one. The change keeps the badge's own lines byte for byte and adds listeners around them. A badge a drop newly raises is pulled back in the same dispatch, so it never paints, and it paints only if no fresh frame has come 1 s (_RECONN_BADGE_HOLD_MS) after the later of the drop and the page turning visible. The hold delays the first paint and never clears anything: romp:wsfresh still clears the badge, a painted badge stays painted on a repeat drop, hiding the page cancels a pending hold, and turning visible re-holds a pending or painted badge. The hold is a time because no event separates a hung first dial from a slow good one. The project's main carries the same badge lines (read 2026-10-02), so it flashes the same way.

An offer to the project carries the hold alone. It drops three fork-only parts of the same block: the shell latch, which keeps the badge's 30 s failsafe from running on a page that has heard the fork shell's link word, so a painted badge there stays until the pane's first fresh frame (rsh, its term in rfail and the message listener; inert without that shell, since upstream's shell publishes no link, so every page upstream keeps the failsafe); ReconnectBadgeHold's cases that drive the link word; and the parked latch (rpk, the romp:parked and romp:unpark listeners, and ReconnectBadgeHold's parked cases), which holds the badge with no timer while the fork's shim has a pane parked and starts the hold at its tap, inert without that shim since upstream's shim parks nothing. The fork's other half of the change, the reconnect detail line in the Log, lives in the fork-only shell code and is not part of an offer. The one-second hold awaits the fork owner's word (it is proposed, not ruled), so an offer waits for it too.
