---
title: Hidden panes park their return redial on the phone
status: candidate
where: kernel/kernel.py: _shim (onScreen from the shell panes word, parentMobile() reading the shell layout probe, park(), the connect() guard, the parked branch in the visibility fast path, the show handler in the panes message listener, the return-fresh parked stamp in send()); _LANDING_ERRS_JS (parked is its own wsState, never down)
added: 2026-09-18
pr:
tier: fix
offered:
closed:
---
D2 of the phone reconnect plan, phone-only by the user ruling of 2026-09-18. On the phone every pane redialed at every return from the background and each took a whole connect push (feed frames, bars) on one link and one thread in the same second as the visible chat. Now a pane whose last panes word from the shell says it is off screen, on the phone layout (the shell _MOBILE_MQ probe read synchronously, the way D3 reads the link), puts its socket down for every state at a stale return (its own park(): abandon() teardown, one wsState word parked, romp:wsdown for the bundle and loader), files its return row with parked true and dials nothing (connect() guard, no awaitLink) until the shell word says its tab is on screen; the tap opens a fresh return window, re-raises the loader and dials once through D3 link rule, and the return-fresh says parked. The desktop layout and standalone pages are unchanged; a pane hidden since load still makes its first dial. The shell keeps parked as its own state so the connection cue and log stay silent. All shim lines are inserted fork-only lines; no upstream shim line is modified. Touches CLIENT_DIAG_KEYS (pane-shim gains parked, a bool approved field by field). Until K2 (kernel-side, joint with romp-performance-1) the tap costs one full frame for the opened pane only. Stacked on PR 4 (iosperf-shell-led), itself on 765 and 762. Offer waits on the user word under the no-new-upstreaming rule (2026-09-11).
