// What a page reload costs the chat pane's reader, and how it comes back (T265, the user 2026-09-08: the dashboard
// reloads itself on a kernel restart and on a newer served bundle — superseding their 2026-07-13 preference for a
// banner the reader clicks — so the reload must not cost them their place). The draft and the active tab were
// persisted already; the active tab's scroll position and follow mode were not, so every reload landed the reader
// at the bottom of the transcript they were reading.
//
// Before the page goes down (the reload core calls window.__rompPersistForReload synchronously; `pagehide` is the
// belt for any other navigation) render.ts records the active shown view's scrollTop, its follow mode (`stick`)
// and its anchor turn (uuid + offset), keyed by the tab id, in the persisted webview state. On load the record is
// taken out of the state at once (one reload, one restore) and landActive's first show of THAT tab consumes it:
// a follow-mode reader lands at the bottom as before; anyone else lands on their anchor turn when the rebuilt DOM
// has it, else on the raw scrollTop. Any other tab, or a second land, sees the ordinary rule. Pure, so node
// executes the decisions; render.ts's wiring is pinned by reload-restore.test.ts.
//
// The anchor carries the reader's LINE inside the anchor turn as well (`at`, reading-point.ts; the review of iOS item 6,
// 2026-10-02), and the restore lands that line when the fresh turn holds it. The turn's top alone is right only when the turn
// lays out as it did before the reload, and a turn with formulas does not: the record is taken over KaTeX's layout and the
// fresh page lands it over formulas still waiting for the math renderer, which are shorter, so the reader's line sat off by
// their growth until the renderer arrived and then jumped. tests/test_math_chunk_served.py holds the landing in both engines.

import type { ReadingPoint } from "./reading-point";

export interface ReloadScroll { id: string; top: number; stick: boolean; anchor: { uuid: string; y: number; at?: ReadingPoint } | null; }

/** The record to persist for the active shown view; null when there is nothing to keep (no active tab). */
export function reloadScrollRecord(id: string | null | undefined, top: number, stick: boolean,
                                   anchor: { uuid: string; y: number; at?: ReadingPoint } | null | undefined): ReloadScroll | null {
  if (!id) return null;
  return { id, top, stick, anchor: anchor || null };
}

/** The saved record applies to exactly one land: the first show of the tab that was active when the page went
 *  down. Anything else (a different tab, a malformed record) gets nothing. */
export function takeReloadScroll(saved: unknown, id: string | null | undefined): ReloadScroll | null {
  const s = saved as ReloadScroll | null | undefined;
  if (!s || typeof s !== "object" || !id || s.id !== id || typeof s.top !== "number") return null;
  return s;
}

/** Where the restored land goes: the bottom for a follow-mode reader, the anchor when the rebuilt DOM honoured it,
 *  else the raw saved scrollTop. */
export function reloadLandTarget(s: ReloadScroll, anchorRestored: boolean): "bottom" | "anchor" | number {
  if (s.stick) return "bottom";
  if (anchorRestored) return "anchor";
  return s.top;
}
