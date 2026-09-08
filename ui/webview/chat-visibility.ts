// The chat page's word for the kernel's pane shim (round 3 of the 2026-09-08 fold). The shim gates its stale
// banner on paneHidden(): a hidden pane never raises it (the 2026-08-15 phone fix, where every hidden pane's
// throttled watchdog raised the banner over a working dashboard). The shim's own measure is the zero-viewport
// probe, which in Chromium is right only for a pane hidden SINCE LOAD: a display:none iframe keeps the size of
// its last show there, so the probe misses every pane the shell hides after the user has looked at it, which on
// the phone shell is the chat pane on every switch to another tab (the chat is the pane shown first). Firefox
// zeroes the hidden iframe's viewport instead and does not run its observer; the shim takes the union of the
// probe and the word, right in both. The panes that gate their paint
// (feed.ts, fleet.ts, waiting.ts, the timeline) publish their gate's two measures as the shim's word (paint-gate.ts
// publishPaneHidden, the one place the flag is named); the chat gates nothing, so this module publishes the same union from the
// same two events: the tab's visibilitychange and an IntersectionObserver over the page's body, which reports
// a display:none iframe as not intersecting and fires again on the way back. No timer, and nothing from the
// shell's panes message (the fork's 2026-09-06 hold read that; steer 2 of the fold replaced it with each frame's
// own visibility). Until the observer has spoken nothing is published and the shim's probe decides; without an
// observer the probe stands for good. Injectable so node --test runs it; the browser leg runs the real thing.
import { publishPaneHidden, type PaneHiddenHost } from "./paint-gate";

export interface ObserverEntryLike { isIntersecting: boolean; }
export type ObserverCtor = new (cb: (entries: ObserverEntryLike[]) => void) => { observe(target: Element): void };
export interface ChatVisibilityDeps {
  doc: { readonly hidden: boolean; addEventListener(type: "visibilitychange", listener: () => void): void };
  win: PaneHiddenHost;
  Observer: ObserverCtor | null;
}

/** Publish the chat page's hidden word on its own events. `root` is the element the observer watches (the
 *  page's body); with no root or no observer nothing is installed and nothing published. */
export function watchChatVisibility(root: Element | null, deps: ChatVisibilityDeps): void {
  if (!root || !deps.Observer) return;
  let intersecting: boolean | null = null;   // the observer's last word; null until it speaks
  const publish = () => { publishPaneHidden(deps.doc.hidden, intersecting, deps.win); };
  new deps.Observer((entries) => { intersecting = entries.some((e) => e.isIntersecting); publish(); }).observe(root);
  deps.doc.addEventListener("visibilitychange", publish);
}

/** The page's own measures, for render.ts. */
export function browserChatVisibilityDeps(): ChatVisibilityDeps {
  return {
    doc: document,
    win: globalThis as PaneHiddenHost,
    Observer: typeof IntersectionObserver === "undefined" ? null : IntersectionObserver,
  };
}
