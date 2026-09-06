// THE SECTION SNAPSHOT, VIEW SIDE (the round-2 review of the tabsnapshot branch): the rules render.ts
// applies to the snapshot pane that are not about what a row SAYS (tab-snapshot.ts owns the model and its
// words) but about how the pane behaves under the strip's events: which row click may open a session.
// PURE, shaped on the minimal "Like" views of render.ts's state (the tab-state.ts idiom), so each rule
// executes in node tests without a DOM (tab-snapshot-view.test.ts); render.ts wires them.

/** Whether a snapshot row's click may open its session: the session the row showed must still be on the
 *  strip. Click safety keeps the pressed row in the DOM until the release (tabPointerHeld), so a session
 *  dismissed between mousedown and mouseup (the kernel's closed frame, a tabOrder push without it) is still
 *  under the click; opening that id put up a loader for a session that never arrives, because the strip's
 *  meta lingers until the next tabOrder frame. A row that had a frame needs its session; a placeholder row
 *  (no frame yet, `loading`) needs its meta, or the frame that landed meanwhile; a tab the user closed
 *  (closingTabs) is neither. `row` is the model row the click landed on; none (never expected) defers to
 *  the session. */
export function rowStillOpen(row: { loading: boolean } | undefined, hasSession: boolean, hasMeta: boolean, closing: boolean): boolean {
  if (closing) return false;
  if (hasSession) return true;
  return !!row?.loading && hasMeta;
}
