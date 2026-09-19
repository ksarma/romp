---
title: Federated remote sockets announce caps=feedDelta and federation applies a remote host feedDelta per host
status: candidate
where: ui/webview/federation.ts (REMOTE_DIAL_CAPS, remoteDialUrl, inboundNow feedDelta branch, applyRemoteFeedDelta, closeRemote), ui/webview/federation-remote-feed-delta.test.ts, ui/webview/feed-delta.test.ts, tests/test_federated_feed_delta_served.py
added: 2026-09-18
pr: 815
tier: fix
offered:
closed:
---
Since the federated dial terms (8fe70da07, 2026-09-15) the remote dial carries delta=1 and no caps, so a remote kernel serves its feed on the view-delta slot path ({type:"delta", slot:"feed"}); nothing on the hub side decodes one (the shim reassembles view deltas on its local socket alone, federation.ts applied feedDelta for the local host only), so a remote Outline, feed or Waiting pane froze after the first full frame, the Outline filed a delta-unapplied row per dropped frame and posted a needSlot the local kernel could not answer (86 rows in 2.4 minutes on the user phone). The remote dial now announces caps=feedDelta (the decoder is federation.ts, so the announcement is its own), a remote feedDelta applies onto the raw frame held per host and is prefixed whole, and a no-base delta asks the sending kernel for a full frame on its own socket. Upstream code (upstream/main carries the same remoteDialUrl); kept in the fork for now, no upstreaming.
