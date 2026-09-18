---
title: The shell leads the visible pane return redial
status: candidate
where: kernel/kernel.py: _shim (parentLink, awaitLink, the link-up dial with linkUpMs, the panes message listener, the 20 s link-backstop, the returnDiag linkUpMs hook, the onclose re-await); _LANDING_MOBILE_JS shellWS (the shell socket gains the shim liveness rules: one live attempt, lastRecv and freeze/resume stamps, a 5 s watchdog, the refused ladder and the 15 s connect cut, the return-probe row, window.__rompLink); _LANDING_COLLAPSE_JS panesMsg (the link field)
added: 2026-09-18
pr:
tier: fix
offered:
closed:
---
D3 of the phone reconnect plan. On the phone a return from the background found every pane socket dead and thirteen independent reconnect machines dialed a down path at once; the refused regime was a dial storm (236 dials per pane in 30 s, harness baseline). The shell socket becomes the page one probe with the shim liveness rules (one attempt in flight); it files one shell clientDiag return-probe row per return and publishes the page link synchronously (window.__rompLink) and as a link field on the panes word, re-told on its open, close and abandon. A pane returning with a dead socket puts it down for every socket state (the watchdog tick inert), files its return row, and dials at once when the link is up at the decision or on the link-up word otherwise (awaitLink), recording linkUpMs in its return-fresh; a loud link-backstop dials anyway when the shell connT is 20 s stale. Independent of PR 3 (hidden panes park). No shared fragment inlined into the shim: the shell keeps its own copy of the liveness rules, pinned to agree with the shim by one test. Touches CLIENT_DIAG_KEYS (the shell return-probe keys and the pane-shim awaitLink and linkUpMs). Stacked on PR 765 (relay redials wait for the local socket), itself on PR 762 (the beacon extension). Offer waits on the user word under the no-new-upstreaming rule (2026-09-11).
