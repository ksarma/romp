---
title: An unhandshaken socket's first frame stands as a proto-1 handshake, so an older page against a newer kernel is served the index wire instead of silence
status: candidate
where: kernel/kernel.py (the chat READY gate); docs/read-side.md
added: 2026-09-18
pr:
tier: fix
offered:
closed:
---
Since b0fabb0a7 (T386 stage 2, round eleven) _send_chat_locked withholds every chat frame from a socket until it declares its wire by a ready message or a reconnect=1&proto dial term. A hub page older than the federation's remote ready (f7a80efee) relays to a newer kernel with no proto term and never posts ready on the relay socket, and a pane shim older than the redial's proto term redials after a restart with reconnect=1 alone; both were held silent for the socket's life, strips flowing and every session body withheld (an older dashboard attached to a newer kernel listed the remote's tabs with nothing behind them, 2026-09-18: two relay sockets, 965 and 644 chat frames withheld, chatWithheld rows on the record). The fix is event-based and inside the gate: _implicit_handshake, called first in _dispatch_ws, takes the FIRST client frame from an unhandshaken socket that is ready from accept as a proto-1 handshake (not a ready, which the arm handles; not a socket held under readyGate, whose shim flushes queued clientDiag rows before the bundle's ready; not msg None), stamps proto 1, wakes the pusher and says so once on stderr; a socket that sends nothing keeps upstream's behaviour (no chat frame, the chatWithheld row at close). Tests: the decision table and the wire it brings (tests/test_chat_window_spans.py) and a real Handler._ws drive of a bare relay dial that never says ready and then sends needFull, answered with a session frame on the index wire (tests/test_chat_pages.py, RealArm); both red on main's kernel.py. docs/read-side.md corrected: it said an unannounced socket is served from accept, false for chat frames since b0fabb0a7. Upstream's own code; whether it is offered is the user's per-PR word.
