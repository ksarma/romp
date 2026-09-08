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
//
// `intersecting` is the observer's LAST WORD, and null until it has spoken (the callback has not fired yet,
// or the page has no IntersectionObserver). For the paint that measure then holds nothing, exactly what the
// panes' earlier `true` default did; the shim's word below is where null makes a difference.
export function paintHeld(docHidden: boolean, intersecting: boolean | null, hasContent: boolean): boolean {
  if (!hasContent) return false;
  return docHidden || intersecting === false;
}

// The release events' shared decision: a paint is owed (dirty) AND both measures now say the pane can be
// seen. visibilitychange→visible on a pane that is still display:none waits for the observer; an observer
// callback inside a hidden tab (a resize while away) waits for the tab. The caller paints SYNCHRONOUSLY on
// a true: on a tab switch the compositor shows the cached frame until the page paints, so a paint inside
// the event handler is the earliest fresh frame — a requestAnimationFrame hop would be one frame later at
// best, and held indefinitely in a display:none frame.
export function paintReleased(dirty: boolean, docHidden: boolean, intersecting: boolean | null): boolean {
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
// callback, visibilitychange, the release) and never on a timer. The shim says hidden when EITHER its probe or
// a published word of true says so: Firefox is Chromium's mirror image (a display:none iframe's viewport reads
// 0 there, and its IntersectionObserver does not run, so the word goes stale while the probe is right), and the
// union is right in both. Until the first event the flag is unset, and the probe alone decides. `w` is the
// page's window (globalThis in a page); the tests hand in a stand-in.
//
// NOTHING is published until the observer has spoken (round 3 of the same fold). A page loaded in a
// background tab gets no observer callback until the tab's first rendering step after its return, so the
// return's visibilitychange arrived first and published the visible verdict for a pane that was
// display:none, one rendering step before the observer's first entry corrected it, and the shim preferred
// that boolean over its probe, which read innerWidth 0 and was right. While the word is null the probe
// decides on both arms: a pane hidden since load reads 0, a shown pane reads its size, and a page with no
// IntersectionObserver keeps the probe for good rather than reading hidden forever after its first tab hide.
export interface PaneHiddenHost { __rompPaneHidden?: boolean; }
export function publishPaneHidden(docHidden: boolean, intersecting: boolean | null, w: PaneHiddenHost = globalThis as PaneHiddenHost): boolean | null {
  if (intersecting === null) return null;   // the observer has not spoken: nothing published, the probe decides
  const hidden = docHidden || !intersecting;
  w.__rompPaneHidden = hidden;
  return hidden;
}
