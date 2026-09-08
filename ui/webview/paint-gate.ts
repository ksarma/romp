// Paint only when the pane can be seen (the user 2026-09-07, whose dashboard froze for seconds on the
// return to its browser tab). Every pane APPLIES every frame it receives the moment it arrives — the model,
// the badge mirror, the follow-move reconciliation — but the PAINT (the feed's render(), the board pane's
// rebuild) is owed, not done, while nobody can see it: the tab is hidden, or the pane sits in a
// display:none iframe. Two measures, because each is blind to the other's case: `document.hidden` is per
// TAB and never reports a display:none pane; an IntersectionObserver reports the pane but never fires
// while the tab is hidden, and not on the return either (nothing intersected differently). So both events
// release — visibilitychange→visible and the observer's callback — and this is the decision they share.
// Pure and DOM-free so node --test executes it; feed.ts and fleet.ts pass their own measures in.
//
// The FIRST content always paints through: an empty list is the pane loader's "still loading" state (the
// loader retires on the list's first child — kernel _pane_spin's MutationObserver), so withholding it would
// reveal a pane with the loader fading over nothing (the 2026-09-04 board-pane bug, now the shared rule).
export function paintHeld(docHidden: boolean, intersecting: boolean, hasContent: boolean): boolean {
  if (!hasContent) return false;
  return docHidden || !intersecting;
}

// The release events' shared decision: a paint is owed (dirty) AND both measures now say the pane can be
// seen. visibilitychange→visible on a pane that is still display:none waits for the observer; an observer
// callback inside a hidden tab (a resize while away) waits for the tab. The caller paints SYNCHRONOUSLY on
// a true: on a tab switch the compositor shows the cached frame until the page paints, so a paint inside
// the event handler is the earliest fresh frame — a requestAnimationFrame hop would be one frame later at
// best, and held indefinitely in a display:none frame.
export function paintReleased(dirty: boolean, docHidden: boolean, intersecting: boolean): boolean {
  return dirty && !paintHeld(docHidden, intersecting, true);
}

// THE SHIM'S WORD (the 2026-09-08 fold's round-2 ruling; the fork's 2026-09-06 hidden-pane read, given a
// publisher again). The kernel's pane shim gates its stale banner on paneHidden(): a hidden pane never raises
// it (the 2026-08-15 phone fix, where every hidden pane's throttled watchdog raised over a working dashboard).
// The shim's own measure is the zero-viewport probe, which is right only for a pane hidden SINCE LOAD: a
// display:none iframe keeps the size of its last show (Chromium: innerWidth 0 hidden since load, 600 once
// shown and hidden again), so the probe misses every pane the shell hides after the user has looked at it,
// the phone shell's every tab switch. The gate already holds the two measures that do not miss it, so each
// pane that gates publishes their union as window.__rompPaneHidden on the gate's own events (the observer's
// callback, visibilitychange, the release) and never on a timer. The shim reads the flag when it is a boolean
// and keeps the probe as the boot fallback: until the first event the flag is unset, and the probe is right
// then. `w` is the page's window (globalThis in a page); the tests hand in a stand-in.
export interface PaneHiddenHost { __rompPaneHidden?: boolean; }
export function publishPaneHidden(docHidden: boolean, intersecting: boolean, w: PaneHiddenHost = globalThis as PaneHiddenHost): boolean {
  const hidden = docHidden || !intersecting;
  w.__rompPaneHidden = hidden;
  return hidden;
}
