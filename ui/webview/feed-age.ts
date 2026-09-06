// The kernel's LIVE clock for a pane that rides the feed payload. Every age a pane shows — "Xm ago", the
// current goal's elapsed time, a recency cutoff — is the difference between a timestamp the KERNEL wrote and
// "now", and the browser's clock can sit minutes from the kernel's (a phone, a laptop back from sleep): read
// against Date.now(), every age on the board is off by that skew. The payload carries the kernel's `now`, but
// only as of the frame, and on the delta path a quiet board sends a pane nothing between the 60 s reposts.
// So the pane keeps the kernel's clock moving itself: it records WHEN the frame arrived and adds the local
// time elapsed since — skew between the two clocks never enters, only the local clock's deltas do. Pure:
// node --test runs it without a DOM.

/** The kernel clock now, in epoch seconds: the last payload's `now` plus the local time since it landed. */
export function liveNow(hostNow: number, hostNowAtMs: number, nowMs: number): number {
  return hostNow + Math.max(0, Math.floor((nowMs - hostNowAtMs) / 1000));
}
