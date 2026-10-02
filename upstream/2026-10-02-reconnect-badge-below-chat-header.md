---
title: The chat's reconnecting badge sits below the chat's header, so it covers none of the header's buttons
status: candidate
where: kernel/kernel.py (_pane_spin's badge placement, rplace); tests/test_pane_loader_reconnect.py (ReconnectBadgeHold placement cases); tests/test_return_from_background_served.py and tests/return_from_background_browser.mjs (the painted badge's box against the header's controls); docs/guide.md (the phone section); upstream/2026-10-02-reconnect-badge-below-chat-header.md (this entry)
added: 2026-10-02
pr:
tier: feature
offered:
closed:
---
The corner badge that says reconnecting over a pane with content (T217) sits at top:8px, right:8px. In the chat page that is over the right end of the header: on a phone it covered 78 percent of the header's tag filter and of its + button, and on a desktop the tab strip's tag filter and its settings gear, for as long as the wait lasted. The change keeps the badge's CSS rule byte for byte and places the badge from its script: in a page with the chat's header (#tabbar), 8 px below the top of the transcript (#content), which is below the header, the strip's resize handle and the pinned notes. A ResizeObserver on the header and the transcript places it again when the chrome above changes size or the pane is shown; no timer. The other panes keep the corner. The project's main carries the same badge rule and the same chat header (read 2026-10-02), so its badge covers the same buttons. In the fork the wait can outlast 30 s, since the failsafe latch keeps the badge up while the shell is still dialing, which made the covered buttons matter more there.

An offer to the project carries the placement (rplace and its observer), its two node cases and the served check of the painted badge's box against the header's controls. The guide sentence it touches sits in the fork's phone paragraph, which the project does not have, so an offer leaves docs/guide.md out.
