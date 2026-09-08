// The chat page's hold on the reload core (the fork's 2026-09-08 fold: T215 meets T265). The core (kernel.py
// _RELOAD_CORE_JS, window.__rompReload on every kernel-served page) reloads the page when the kernel serving it
// restarts. A kernel restart is also the event T215 heals: a file shipped before the restart keeps its encoded
// payload in render.ts's pendingShips, re-ships on the socket's reopen, and its ack retires the chip and releases a
// send held behind the ship gate. On the served /chat page the reload landed about 1.7 s after the relaunch and
// took the in-memory payload with it, so nothing re-shipped, nothing was sent, and the fresh page showed the loss
// toast. Ruling: both stand, the heal first. This word is how the page tells the core: published while any ship
// awaits its ack, in the style of the paint gate's window.__rompPaneHidden (paint-gate.ts publishPaneHidden, the
// one place THAT flag is named; this is the one place this one is). The core reads it in busyHere as the "ships"
// hold, re-checks it on a short timer while it is up, reloads once it clears, and after a bounded wait (60 s)
// reloads anyway with a console line saying why. Derived from the pending-ship count at every change to
// pendingShips, never tracked by hand, so it cannot drift from the strip. `w` is the page's window (globalThis in
// a page); the tests hand in a stand-in.
export interface ReloadHoldHost { __rompReloadHold?: boolean; }
export function publishReloadHold(shipsPending: number, w: ReloadHoldHost = globalThis as ReloadHoldHost): boolean {
  const held = shipsPending > 0;
  w.__rompReloadHold = held;
  return held;
}

// The notices a reload wipes (the same fold, the review's F2). The hold above makes the restart reload FOLLOW the last
// pending ship's retirement, within the core's 500 ms re-check; the two user notices raised at that same moment (a
// dropSaveFailed nack: the attachment was not saved, the held message not sent; the other-tab ack: the held message
// was not sent) are DOM-only toasts that die with the page, and the fresh page's loss toast reads shipsInFlight,
// which that retirement already emptied. So render.ts snapshots the texts of the toasts on screen into the persisted
// state as `pendingNotices` on the CORE's pre-reload hook alone (persistNoticesForReload, called from persistForReload,
// the function window.__rompPersistForReload names; pagehide keeps upstream's scroll record alone, so a load of the
// user's own says nothing twice) and shows them again once at load. Pure here so the two readings run in node; the
// wiring is pinned in reload-hold.test.ts and executed on the served page in tests/test_ship_reship.py.
/** The toast container as the reading needs it: anything with querySelectorAll (a DOM element in the page). */
export interface NoticeBox { querySelectorAll(selectors: string): ArrayLike<{ textContent: string | null }>; }
/** The texts of the warning toasts on screen (#warn-toasts .warn-toast-msg, in DOM order), blanks dropped; none
 *  when the container was never created. */
export function liveNotices(box: NoticeBox | null | undefined): string[] {
  if (!box) return [];
  return Array.from(box.querySelectorAll(".warn-toast-msg"), (n) => (n.textContent || "").trim()).filter((t) => !!t);
}
/** Take the persisted notices out of a state object: the non-empty strings among `pendingNotices` (anything else
 *  reads as none), and the state without the key, for the one-shot write-back. */
export function takePendingNotices(st: unknown): { notices: string[]; rest: Record<string, unknown> } {
  const s = (st && typeof st === "object" ? st : {}) as Record<string, unknown>;
  const raw = s.pendingNotices;
  const notices = Array.isArray(raw) ? raw.filter((x): x is string => typeof x === "string" && !!x) : [];
  const rest = { ...s };
  delete rest.pendingNotices;
  return { notices, rest };
}
