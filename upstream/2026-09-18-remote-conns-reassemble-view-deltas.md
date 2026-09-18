---
title: Federated remote sockets reassemble the kernel view deltas, so a remote host timeline bars move after the first full frame
status: candidate
where: ui/webview/view-deltas.ts (moved from vscode-extension/src/view-deltas.ts), ui/webview/federation.ts (Conn.viewDeltas, openRemote, inboundNow, closeRemote, the REMOTE_DIAL_CAPS and remoteDialUrl comments), ui/webview/fleet.ts (the delta arm comment), ui/webview/federation-remote-view-delta.test.ts, vscode-extension/src/extension.ts, vscode-extension/src/pipe-view-deltas.test.ts
added: 2026-09-18
pr:
tier: fix
offered:
closed:
---
The relay dial carries the page delta=1 term since 8fe70da07 (2026-09-15), so a remote kernel serves its timeline bars slot as {type:"delta", slot:"bars"} patches after the first full frame (kernel.py _send_slot_delta), and the feed the same way on a remote too old to read the caps term. Nothing on the hub side reassembled one: the kernel inline shim decodes only its own local socket, and federation.ts had no arm for the type, so the raw patch fell through to the pane and timeline-boot.ts dropped it without a row; a remote host lanes froze on the phone where its first full frame put them. Now the ViewDeltas receiver VS Code pipe already used (moved to ui/webview) runs once per remote Conn on the raw frame before prefixing: a patch continues as the reassembled whole frame down the bars and feed arms, and one it cannot apply asks the kernel that sent it for the whole slot (needSlot) on its own socket, never the local kernel. delta=1 stays on the dial: dropping it would make every remote a whole-frame client, a whole bars frame per change plus the 60 s repost (kernel.py _DEDUP_REPOST_S) per remote host on an idle board. Upstream code (upstream/main carries the same remoteDialUrl and the extension receiver); kept in the fork for now, no upstreaming.
