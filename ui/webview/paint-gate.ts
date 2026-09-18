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
// `intersecting` is the observer's LAST WORD, and null until it has spoken (the callback has not fired yet, or
// the page has no IntersectionObserver). For the paint that measure then holds nothing, exactly what the panes'
// earlier `true` default did; publishPaneHidden below is where null makes a difference.
export function paintHeld(docHidden: boolean, intersecting: boolean | null, hasContent: boolean): boolean {
  if (!hasContent) return false;
  return docHidden || intersecting === false;
}

// THE FIRST PAINT ON THE PHONE (stage 0 of the reconnect design, 2026-09-18). paintHeld lets the first content through
// whatever the visibility, for the pane loader's sake. On the phone shell a pane off screen at its first frame has nobody to
// show the loader to either: the feed pane loads at boot behind the chat tab (its socket feeds the shell's bell, the parking
// rule's exemption), applies its first frame, and painted a board of hundreds of cards into a display:none iframe, work the
// visible chat's main thread paid for. So on the phone (the shell's layout probe, window.parent.__rompMobileOn, read by the
// pane as the shim reads it) the first paint is held too while the pane is off screen: by the shell's panes word when one has
// arrived (on[app] false; the shell posts it on the pane's load and on every tab switch), else by the shim's zero-viewport
// probe (a frame hidden since load reads 0 in every browser) or the observer's word. The frame is APPLIED all the same (the
// badge mirror rings the bell from it); the shell's word on the pane's show releases the paint (feed.ts treats the word as the
// observer's, the revealCard precedent), as does the observer's own callback when the iframe shows. Off the phone (undefined,
// false: the desktop grid, a standalone page, the VS Code webview) nothing changes.
export function firstPaintHeld(hasContent: boolean, phone: boolean | undefined, shellOn: boolean | undefined, probeHidden: boolean, intersecting: boolean | null): boolean {
  if (hasContent || phone !== true) return false;
  if (shellOn !== undefined) return !shellOn;
  return probeHidden || intersecting === false;
}

// The shim's zero-viewport probe, read off a window: a framed pane whose viewport is 0 by 0 has been hidden since load (every
// browser lays a shown frame out, so a shown pane never reads 0). The first-paint hold's fallback above, before the shell's
// word or the observer has spoken, and nothing else's: a pane hidden AFTER a first show keeps its size in Chromium, which is
// why the standing gate reads the observer's word and never this (feed-age.test.ts pins feed.ts to carry no probe of its own).
export function viewportHiddenSinceLoad(w: { parent: unknown; innerWidth: number; innerHeight: number }): boolean {
  try { return w.parent !== w && (w.innerWidth === 0 || w.innerHeight === 0); } catch { return false; }
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

// THE PANE'S HIDDEN WORD. The kernel's pane shim gates its stale banner on paneHidden(): a pane the user cannot
// see never raises it (the 2026-08-15 phone fix, where every hidden pane's throttled watchdog raised the banner
// over a working dashboard). Whether the user can see a pane has two witnesses, and every consumer of that
// question reads their union. The shim's own witness is the zero-viewport probe (innerWidth or innerHeight 0
// inside a frame): right for a pane hidden since load in any browser, and in Firefox always, but blind in
// Chromium to a pane hidden AFTER a first show, because a display:none iframe keeps the size of its last show
// there. Once the user has looked at a pane (the phone shell's every tab switch), the probe reads it as shown.
// The gate's two measures are the other witness, right for exactly that case, so each pane publishes their
// union as window.__rompPaneHidden on the gate's own events (the observer's callback, visibilitychange on both
// arms, the release), never on a timer. Firefox is the mirror image: the hidden iframe's viewport reads 0 (the
// probe is right) and its IntersectionObserver does not run (the word stays at its last verdict), so a consumer
// says hidden when EITHER its probe or a published word of true says so, and never reads the word first. `w` is
// the page's window (globalThis in a page); the tests hand in a stand-in.
//
// NOTHING is published until the observer has spoken. Before its first entry the pane has measured nothing: a
// page loaded in a background tab gets no observer callback until the tab's first rendering step after its
// return, so the return's visibilitychange runs first, and a word published then would be document.hidden
// alone, which says visible for a display:none pane. The probe covers that moment (a never-shown frame reads 0
// in every browser), so the pane stays silent and the probe decides on both arms; a page with no
// IntersectionObserver keeps the probe for good.
export interface PaneHiddenHost { __rompPaneHidden?: boolean; }
export function publishPaneHidden(docHidden: boolean, intersecting: boolean | null, w: PaneHiddenHost = globalThis as PaneHiddenHost): boolean | null {
  if (intersecting === null) return null;   // the observer has not spoken: nothing published, the probe decides
  const hidden = docHidden || !intersecting;
  w.__rompPaneHidden = hidden;
  return hidden;
}
