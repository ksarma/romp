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

/** What installSnapshotEscape needs of the page: `showing` (the snapshot is up), `typing` (the target keeps its
 *  own Escape: a field, an editable), `layerOpen` (a layer of this page owns Escape right now: a menu, the
 *  picker or a confirm overlay, a panel, a preview, a comment thread) and `leave` (the exit). */
export interface EscapeHooks { showing(): boolean; typing(target: EventTarget | null): boolean; layerOpen(): boolean; leave(): void }
export interface EscapeTarget { addEventListener(type: "keydown", fn: (e: KeyboardEvent) => void, capture?: boolean): void }

/** ESCAPE LEAVES THE SNAPSHOT, and yields to every layer that owns its own Escape, in two phases on one
 *  window. ARMED at the window's capture phase, so this page's layers are still on the page to be seen (a
 *  menu closes itself on Escape and is gone by the bubble); an Escape a listener registered before this one
 *  already marked (the tab menu's closer) is not ours. DECIDED at the window's bubble phase, after the SHELL's
 *  Escape chain has run: its panels (the log, usage and network panels) live in the shell document, out of
 *  this page's sight, and its chain sits on this frame's DOCUMENT at capture (kernel.py _LANDING_ESC_JS), so
 *  it runs after the arm and before the decision, and marks and stops the Escape it consumed, which then
 *  never reaches the decision. The round-2 review: the one-phase capture handler swapped the pane on an
 *  Escape aimed at the log panel. The arm is the event itself, checked by identity at the bubble, so an
 *  Escape stopped between the phases leaves nothing a later key can inherit. */
export function installSnapshotEscape(win: EscapeTarget, hooks: EscapeHooks): void {
  let armed: KeyboardEvent | null = null;
  win.addEventListener("keydown", (e) => {
    armed = null;
    if (e.key !== "Escape" || !hooks.showing() || e.defaultPrevented) return;
    if (hooks.typing(e.target) || hooks.layerOpen()) return;
    armed = e;
  }, true);
  win.addEventListener("keydown", (e) => {
    if (e !== armed) return;
    armed = null;
    if (e.defaultPrevented || !hooks.showing()) return;
    e.preventDefault();
    hooks.leave();
  }, false);
}
