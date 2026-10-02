---
title: The reconnecting badge sits below each pane's header, so it covers none of the header's controls
status: candidate
where: kernel/kernel.py (_pane_spin's badge placement, rplace); tests/test_pane_loader_reconnect.py (ReconnectBadgeHold placement cases); tests/test_return_from_background_served.py and tests/return_from_background_browser.mjs (the painted badge's box against the pane's chrome controls); docs/guide.md (the phone section); upstream/2026-10-02-reconnect-badge-below-pane-header.md (this entry)
added: 2026-10-02
pr:
tier: feature
offered:
closed:
---
The corner badge that says reconnecting over a pane with content (T217) sits at top:8px, right:8px. In every pane page that is over the right end of the pane's header. In a hermetic lab on the fork, on a phone it covered 78 percent of the chat header's tag filter and of its + button, and 88 percent of the Outline's tag filter and part of its search field; on a desktop it covered the chat tab strip's tag filter and its settings gear. The controls stayed hidden for as long as the wait lasted. The change keeps the badge's CSS rule byte for byte and places the badge from its script: 8 px below the top of the pane's content container (the cid _pane_spin is given) when that container is the pane's scroll area (overflow-y auto or scroll), which every pane page has under its header (the chat's transcript, #content; the Outline's, the Feed's and the Waiting pane's lists, each its pane's <pane>-list). A scroll area's box does not move when it scrolls, so a ResizeObserver on it and on the page places the badge again when the chrome above changes size, the pane is shown or the window is resized; no timer. A container that is not a scroll area keeps the corner. The project's main carries the same badge rule and the same pane layouts (read 2026-10-02), so its badge covers the same controls. In the fork the wait can outlast 30 s, since the failsafe latch keeps the badge up while the shell is still dialing, which made the covered controls matter more there.

An offer to the project carries the placement (rplace and its observer), its node cases and the served check of each painted badge's box against the pane's chrome controls (the Outline's outage-tap leg is fork-only: it taps a pane the fork's shim parked). The guide sentence it touches sits in the fork's phone paragraph, which the project does not have, so an offer leaves docs/guide.md out.
