// The notices a reload wipes (the fork's 2026-09-08 fold, the review's F2). The reload core (kernel.py _RELOAD_CORE_JS,
// window.__rompReload on every kernel-served page) reloads the page when the kernel serving it restarts, and a kernel
// restart is also the event T215 heals: a file shipped before the restart keeps its encoded payload in render.ts's
// pendingShips, re-ships on the socket's reopen, and its ack retires the chip and releases a send held behind the ship
// gate. The page's HOLD on that reload is upstream's (T272): render.ts wraps the shim's window.__rompPaneBusy and answers
// 'upload' while any ship awaits its ack and 'held-send' while the ship gate holds a send, and tells the core the
// ending event through window.__rompReload.ended() (render.ts endReloadHoldIfIdle). This module once published the
// fork's own word for the same hold (window.__rompReloadHold, read by the core as a 'ships' hold); the 2026-09-09 fold
// converged the core on upstream's shape and the publisher retired (reload-hold.test.ts names the ruling). The fork's
// 60 s DEADLINE on that hold stays in the core as the backstop (the fold's ruling): a pane word that has blocked an owed
// reload for 60 s is released, the console names it, and the core hands the pane a note through
// window.__rompReload.released() for the fresh page (releasedNotices below reads it into the persisted toasts). What
// else stays is the other half of that fold: the restart reload FOLLOWS the last pending ship's retirement, and
// the two user notices raised at that same moment (a dropSaveFailed nack: the attachment was not saved, the held
// message not sent; the other-tab ack: the held message was not sent) are DOM-only toasts that die with the page, and
// the fresh page's loss toast reads shipsInFlight, which that retirement already emptied. So render.ts snapshots the
// texts of the toasts on screen into the persisted state as `pendingNotices` on the CORE's pre-reload hook alone
// (persistNoticesForReload, called from persistForReload, the function window.__rompPersistForReload names; pagehide
// keeps upstream's scroll record alone, so a load of the user's own says nothing twice) and shows them again once at
// load. A toast about the connection itself (the session isn't reachable, the host is disconnected) is left out:
// render.ts ephemeralWarnToast marks it data-ephemeral, since it was true of the page that raised it and the restart
// reload follows the reconnect. Pure here so the two readings run in node; the wiring is pinned in reload-hold.test.ts
// and executed on the served page in tests/test_ship_reship.py.
/** The toast container as the reading needs it: anything with querySelectorAll (a DOM element in the page). */
export interface NoticeBox { querySelectorAll(selectors: string): ArrayLike<{ textContent: string | null }>; }
/** The texts of the warning toasts on screen (#warn-toasts .warn-toast-msg, in DOM order), blanks dropped and the
 *  toasts marked data-ephemeral skipped (a notice about the connection itself; see the note above); none when the
 *  container was never created. */
export function liveNotices(box: NoticeBox | null | undefined): string[] {
  if (!box) return [];
  return Array.from(box.querySelectorAll(".warn-toast:not([data-ephemeral]) .warn-toast-msg"), (n) => (n.textContent || "").trim()).filter((t) => !!t);
}
/** The reload core's own notice for the reload it is firing, as the list persistNoticesForReload appends to the live
 *  toasts: the core's 60 s backstop (kernel.py _RELOAD_CORE_JS `clock`) released a pane word that never ended (an upload
 *  with no ack or nack, a send held behind it; the shim's 'sends' has no deadline), and the note says what
 *  the page waited for and that it stopped waiting; a reload that fired on the hold's own event has none. Reads the core
 *  handed in (window.__rompReload on a kernel-served page; a pane's answers with its shell's, since the shell decided),
 *  so a page without the core (the VS Code webview), an older core without the accessor, or a throwing one reads as
 *  none. */
export function releasedNotices(core: unknown): string[] {
  try {
    const fn = (core as { released?: unknown } | null | undefined)?.released;
    const text = typeof fn === "function" ? fn.call(core) : "";
    return typeof text === "string" && text ? [text] : [];
  } catch { return []; }
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
