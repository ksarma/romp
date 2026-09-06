// The feed's LIVE clock and its age refresh (2026-09-03). Every "Xm ago" and recency tint on the board is
// computed from the kernel's clock (`now` on the last payload), never the browser's — the two can differ
// by minutes. Since the delta path sends a quiet board NOTHING (the kernel used to repost the frame every
// 60 s, so that clock was never more than a minute stale), the pane keeps the clock moving itself: it
// records WHEN it received the payload and adds the local time elapsed since (liveNow), so skew between
// the two clocks never enters — only the local clock's deltas do. Age-bearing elements are STAMPED with
// their timestamp (data-age-t) and format, so one refresh pass (refreshAges) repaints every one of them —
// ask cards, group cards, sub-goal rows, an open modal — from the same clock, rather than each render
// path owning a copy of the formatting. Pure functions: node --test runs them without a DOM.
//
// The refresh WRITES ONLY WHAT CHANGED (2026-09-06). It used to set every stamped label's textContent
// every 15 s, changed or not, and that cost 69-119 ms of style and layout per tick on an 800-card board
// (the headless-Chrome bench, tools/ui-bench.mjs, PR #227: 10-12 ms of script, the rest layout). The reason the compare is
// needed, and must stay: Blink short-circuits an identical textContent write only in a document that has
// never created a MutationObserver. gear.js creates several at boot (the settings modal's pickers), and the
// flag is permanent once set — any other observer, a browser extension's included, sets it too — so in
// every romp pane an identical textContent write replaces the Text node and dirties layout. Only 2-13 of
// 810 labels actually change per tick (relAge rounds to the minute, then the hour), so comparing first
// removes the whole cost. The colour compares against a shadow value, not the CSSOM read-back, which
// re-serialises the string (spaces after the commas) and would never match.
import { workingFor } from "./spin-caption";

/** The kernel clock now, in epoch seconds: the last payload's `now` plus the local time since it landed. */
export function liveNow(hostNow: number, hostNowAtMs: number, nowMs: number): number {
  return hostNow + Math.max(0, Math.floor((nowMs - hostNowAtMs) / 1000));
}

/** "3m ago" | "(3m ago)" | a running DURATION "42m" / "1h 5m" (the awaiting box's waited time, the
 *  working narration's elapsed time, the waiting-on chip) — the labels that used to be baked into
 *  caption strings and moved only because every card re-rendered on every frame. */
export type AgeFmt = "plain" | "paren" | "dur";

/** The slice of an element the refresh reads and writes — HTMLElement satisfies it; tests use a plain object. */
export interface AgeEl {
  textContent: string | null;
  style: { color: string };
  dataset: { ageT?: string; ageFmt?: string; ageTint?: string };
  _ageC?: string;   // the last tint written (a shadow: the CSSOM re-serialises colours, so it cannot be compared against)
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

/** Repaint one stamped element for `now`, writing only what differs from what it shows. Returns true when
 *  something was written. An element with no stamp (or a non-numeric one) is left alone. */
export function paintAge(el: AgeEl, now: number, rel: (secs: number) => string, tint: (secs: number) => string): boolean {
  const t = Number(el.dataset.ageT);
  if (el.dataset.ageT === undefined || !Number.isFinite(t)) return false;
  const fmt = el.dataset.ageFmt;
  const s = fmt === "dur" ? workingFor(now - t) : rel(now - t);
  const text = fmt === "paren" ? "(" + s + ")" : s;
  let wrote = false;
  if (el.textContent !== text) { el.textContent = text; wrote = true; }
  if (el.dataset.ageTint) {
    const c = tint(now - t);
    if (el._ageC !== c) { el._ageC = c; el.style.color = c; wrote = true; }
  }
  return wrote;
}

/** Repaint every stamped element for `now`; returns how many were actually rewritten. */
export function refreshAges(els: Iterable<AgeEl>, now: number, rel: (secs: number) => string, tint: (secs: number) => string): number {
  let n = 0;
  for (const el of els) if (paintAge(el, now, rel, tint)) n++;
  return n;
}

/** The live pass's visibility gate — the Outline pane's pattern (fleet.ts), shared so the feed and the
 *  Waiting pane run the same one and a test can drive it: `tick` runs the pass unless the pane is hidden
 *  (a hidden tab, or a zero-size iframe the shell has display:none'd), in which case it remembers that a
 *  pass was skipped; `catchUp` (wired to visibilitychange and resize) runs ONE pass if and only if one
 *  was skipped and the pane is visible now — an ordinary resize, or a visibility flip with no skipped
 *  pass behind it, runs nothing. */
export function liveRefresher(opts: { hidden: () => boolean; pass: () => void }): { tick: () => void; catchUp: () => void } {
  let skipped = false;
  const tick = () => {
    if (opts.hidden()) { skipped = true; return; }
    skipped = false;
    opts.pass();
  };
  return { tick, catchUp: () => { if (skipped) tick(); } };
}
