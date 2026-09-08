---
title: Feed pane: repaint only the cards whose inputs changed (`feed-card-gate.ts` keys every board-level input a card reads outside its own object, and a card repaints only when its object identity or that key changed), the 15 s age tick compares before writing text and tint, the glide passes touch only columns whose membership or order changed, and Retry and Revive re-arm on the kernel's error frame
status: offered
where: fork PR #238 (`feed-incremental`, merged 2026-09-06): `ui/webview/feed.ts`, `ui/webview/feed-card-gate.ts` (new), `ui/webview/feed-age.ts`, `ui/webview/spin-caption.ts`, `ui/webview/age-color.ts`, `vscode-extension/src/feed-fly.test.ts`; tests `ui/webview/feed-card-gate.test.ts`, `ui/webview/feed-render-incremental.test.ts` (feed.ts booted under the DOM stand-in, frames A to D), a tick test, and pin updates in the feed test files
added: 2026-09-07
pr: 238
tier: fix
offered: their PR #1061
closed:
---
Upstream's feed pane re-renders every card on every frame, full or delta (class, tint and name nodes rewritten, delegations rebuilt), which invalidates the whole tree, and the scroll restore that follows forces a synchronous layout of all of it: on a recorded stream of about 800 cards a CPU profile put 97% of `render()`'s self time on that one `scrollTop` line, a 542 KB delta cost as much as the 6.6 MB first frame, and the 15 s tick rewrote every card's tint and age label. Bucket placement, the order walk and cross-column removal stay unconditional, so a card whose column or sort changed still moves; quarantine cards never skip; each fly carries a token and a played guard so an interrupted glide finishes instead of snapping. Behaviour notes: cards below a card whose height changed snap into place instead of gliding; a failed Revive re-arms only when the kernel also addresses the feed, which today it does not. Measured in headless Chrome against a build of main on the same recording: a delta's handler 454 to 63 ms, settle 524 to 105 ms, layouts per delta 127 to 5, the tick's long frames gone; the first full frame is unchanged (about 600 ms) and stays a separate item.

Port note: the same age refresher also serves the fork's Waiting on you pane (`ui/webview/waiting.ts`, absent from `upstream/main`; entry `waiting-on-you-pane`), so those hunks are left out of the offer. The measurement came from entry `ui-bench-tool` (#227). Two adversarial review rounds with Chromium reproductions; twenty findings applied.

OFFERED 2026-09-08: offered upstream inside bundle PR #1061 (Panes: direct frame delivery, and chat and feed renders that repaint only what changed; label fix; branch browser-frames-offer; head ac851384; a draft while the branch is rebased onto the moved upstream tip) with `federation-direct-frame-delivery` and the shim's lane identity (P4) and the chat render cuts (P6) of `browser-round2-cuts`; its hidden-pane hold (P2) was dropped at the rebase as covered by upstream's #1016.
