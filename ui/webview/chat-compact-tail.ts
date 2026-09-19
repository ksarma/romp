// Compact mode's tail path by UNIT, the plan (PR E, 2026-09-19; render.ts syncViewInner executes it). In compact mode a unit is one
// compactDisplay item (compact.ts): a lone event, a folded run of tools or notices, or a gap. Before this, every paint that changed or
// appended an event in compact mode rebuilt the whole rendered window (renderWindowItems: every child removed, every unit of the
// current window re-rendered, at least 80), once per animation frame while a turn streamed. The plan names the first unit to
// re-render from, and the trim-and-append the normal-mode tail already does by data-unit takes it from there: the units the DOM was
// last built from (`prev`) against the units now (`items`), and the first changed EVENT the kernel named (`from`, v.rendered).
//
// The first unit to re-render is the earlier of two: the first unit whose item differs (a fold boundary that moved: a tool joining a
// run turns event{n-1} into toolgroup{[n-1, n]}, or extends a run; the unit holding the run's first member is where the lists part),
// and the first unit whose events reach `from` (a growing reply is its own unit; a changed tool inside a run is the run's unit). A run's
// head and, when expanded, its rows all carry the run's unit, so trimming from that unit takes them all and appendItem re-renders the
// run whole: a fold boundary moving needs no rebuild.
//
// The rebuild stays for what a trim from the tail cannot do: a stale view (a reconcile pass touched a prefix event, a tail shrank), no
// record of the units the DOM holds, a first unit below the window's start (the change is among the units the top spacer stands for),
// a gap at or past the first unit (its element and its spacer entry are keyed by unit), a bottom spacer under the window (the trim
// walks up from the last child; a spacer carries no unit and would end it at once). A window the reader browsed away from the tail
// grows its bottom spacer when the change lies below it (the shape normal mode has always had) and rebuilds when the change lies
// inside it, as before. Pure: chat-compact-tail.test.ts executes every rule.
import type { DisplayItem } from "./compact";

export type TailPlan =
  | { kind: "rebuild"; why: "stale" | "no-record" | "below-window" | "inside-browsed" | "bottom-spacer" | "gap" }
  | { kind: "spacer" }                  // the change lies below a browsed window: grow the bottom spacer, touch no node
  | { kind: "append"; u0: number };     // trim the units from u0 off the tail and re-render [u0, items.length)

/** Two display items describe the same unit: the same kind over the same events (a gap over the same turns, before the same event). */
export function sameItem(a: DisplayItem, b: DisplayItem): boolean {
  if (a.kind !== b.kind) return false;
  if (a.kind === "event") return a.index === (b as { index: number }).index;
  if (a.kind === "gap") { const g = b as { lo: number; hi: number; before: number }; return a.lo === g.lo && a.hi === g.hi && a.before === g.before; }
  const bi = (b as { indices: number[] }).indices;
  if (a.indices.length !== bi.length) return false;
  for (let i = 0; i < bi.length; i++) if (a.indices[i] !== bi[i]) return false;
  return true;
}

/** The first unit at which two item lists differ; -1 when they are the same list (the same length, every item the same). */
export function firstDifferingUnit(prev: readonly DisplayItem[], items: readonly DisplayItem[]): number {
  const n = Math.min(prev.length, items.length);
  for (let u = 0; u < n; u++) if (!sameItem(prev[u], items[u])) return u;
  return prev.length === items.length ? -1 : n;
}

/** The last event a unit holds: a lone event its own; a run its last member; a gap none (-1: it stands for turns the page does not hold). */
export function itemLastEvent(it: DisplayItem): number {
  if (it.kind === "event") return it.index;
  if (it.kind === "gap") return -1;
  return it.indices.length ? it.indices[it.indices.length - 1] : -1;
}

/** The first unit whose events reach event `from` (its last event at or past `from`); items.length when none does (every event at or
 *  past `from` is hidden — a thinking block compact mode never shows — or `from` is the length). */
export function firstUnitReaching(items: readonly DisplayItem[], from: number): number {
  for (let u = 0; u < items.length; u++) if (itemLastEvent(items[u]) >= from) return u;
  return items.length;
}

export interface TailWorld {
  prev: readonly DisplayItem[] | undefined;   // the units the DOM was last built from (v.units)
  items: readonly DisplayItem[];              // the units now
  from: number;                               // the first changed event (v.rendered after the tail lowered it)
  winStart: number; winEnd: number;           // the rendered window [winStart, winEnd) before this paint
  unitTotal: number | undefined;              // the unit count at the last build (v.unitTotal)
  stale: boolean;                             // v.stale
  bottomSpacer: boolean;                      // a .tx-spacer-bot stands under the window
}

export function compactTailPlan(w: TailWorld): TailPlan {
  if (w.stale) return { kind: "rebuild", why: "stale" };
  if (!w.prev || w.prev.length !== (w.unitTotal ?? -1)) return { kind: "rebuild", why: "no-record" };
  const total = w.items.length;
  const diff = firstDifferingUnit(w.prev, w.items);
  const reach = firstUnitReaching(w.items, w.from);
  const u0 = Math.min(diff < 0 ? total : diff, reach);
  const atTail = w.winEnd >= (w.unitTotal ?? total);   // the window covered the OLD end (syncViewInner's wasAtTail)
  if (!atTail) return u0 >= w.winEnd ? { kind: "spacer" } : { kind: "rebuild", why: "inside-browsed" };
  if (u0 < w.winStart) return { kind: "rebuild", why: "below-window" };
  if (w.bottomSpacer) return { kind: "rebuild", why: "bottom-spacer" };
  for (let u = u0; u < total; u++) if (w.items[u].kind === "gap") return { kind: "rebuild", why: "gap" };
  return { kind: "append", u0 };
}
