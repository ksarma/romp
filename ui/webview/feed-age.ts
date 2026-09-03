// The feed's LIVE clock and its age refresh (2026-09-03). Every "Xm ago" and recency tint on the board is
// computed from the kernel's clock (`now` on the last payload), never the browser's — the two can differ
// by minutes. Since the delta path sends a quiet board NOTHING (the kernel used to repost the frame every
// 60 s, so that clock was never more than a minute stale), the pane keeps the clock moving itself: it
// records WHEN it received the payload and adds the local time elapsed since (liveNow), so skew between
// the two clocks never enters — only the local clock's deltas do. Age-bearing elements are STAMPED with
// their timestamp (data-age-t) and format, so one refresh pass (refreshAges) repaints every one of them —
// ask cards, group cards, sub-goal rows, an open modal — from the same clock, rather than each render
// path owning a copy of the formatting. Pure functions: node --test runs them without a DOM.

/** The kernel clock now, in epoch seconds: the last payload's `now` plus the local time since it landed. */
export function liveNow(hostNow: number, hostNowAtMs: number, nowMs: number): number {
  return hostNow + Math.max(0, Math.floor((nowMs - hostNowAtMs) / 1000));
}

export type AgeFmt = "plain" | "paren";   // "3m ago" | "(3m ago)"

/** The slice of an element the refresh reads and writes — HTMLElement satisfies it; tests use a plain object. */
export interface AgeEl {
  textContent: string | null;
  style: { color: string };
  dataset: { ageT?: string; ageFmt?: string; ageTint?: string };
}

/** Stamp `el` with its timestamp and format, and paint it for `now`. `tinted` colours the text on the
 *  recency ramp as well (sub-goal rows, the modal's age); card time stamps stay in their own colour. */
export function stampAge(el: AgeEl, t: number, fmt: AgeFmt, tinted: boolean, now: number,
                         rel: (secs: number) => string, tint: (secs: number) => string): void {
  el.dataset.ageT = String(t);
  el.dataset.ageFmt = fmt;
  el.dataset.ageTint = tinted ? "1" : "";
  paintAge(el, now, rel, tint);
}

/** Repaint one stamped element for `now`. An element with no stamp (or a non-numeric one) is left alone. */
export function paintAge(el: AgeEl, now: number, rel: (secs: number) => string, tint: (secs: number) => string): boolean {
  const t = Number(el.dataset.ageT);
  if (el.dataset.ageT === undefined || !Number.isFinite(t)) return false;
  const s = rel(now - t);
  el.textContent = el.dataset.ageFmt === "paren" ? "(" + s + ")" : s;
  if (el.dataset.ageTint) el.style.color = tint(now - t);
  return true;
}

/** Repaint every stamped element for `now`; returns how many were repainted. */
export function refreshAges(els: Iterable<AgeEl>, now: number, rel: (secs: number) => string, tint: (secs: number) => string): number {
  let n = 0;
  for (const el of els) if (paintAge(el, now, rel, tint)) n++;
  return n;
}
