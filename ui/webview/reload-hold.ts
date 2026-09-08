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
