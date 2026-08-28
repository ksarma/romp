// Pure slot geometry for the tab strip's live drag reorder (the drag-flap fix, 2026-08-28; the
// T127 surface). The first implementation hit-tested the LIVE layout — but inserting the
// variable-width provisional tab re-wraps the row, the tab under the cursor changes identity, the
// next hit-test lands on the other side, and the slot oscillates between distant positions while
// the cursor moves smoothly (the user's recording, frames f024–f035). The fix: the pointer is
// hit-tested against a VIRTUAL layout of the NON-dragged tabs only — widths captured once at
// dragstart, the strip's flex-wrap simulated deterministically — so the boundaries cannot move in
// response to the insert they cause. Monotone pointer motion crosses each boundary once by
// construction; no debounce, no heuristics.

export interface SlotBox { id: string; w: number; }

/** Simulate the strip's wrap layout (row fill left-to-right up to `containerW`, `gapX` between
 *  tabs, uniform `rowH`) over the non-dragged boxes, and return the insertion index for pointer
 *  (x, y) in the container's content space: 0..boxes.length, where boxes.length = the end. */
export function dragSlotIndex(boxes: readonly SlotBox[], containerW: number, gapX: number,
                              rowH: number, x: number, y: number): number {
  if (!boxes.length) return 0;
  // lay the boxes into rows exactly as flex-wrap would
  const rows: { start: number; mids: number[] }[] = [];
  let cx = 0, row: { start: number; mids: number[] } | null = null;
  boxes.forEach((b, i) => {
    const needsWrap = row !== null && cx + b.w > containerW && cx > 0;
    if (row === null || needsWrap) { row = { start: i, mids: [] }; rows.push(row); cx = 0; }
    row.mids.push(cx + b.w / 2);
    cx += b.w + gapX;
  });
  const ri = Math.max(0, Math.min(rows.length - 1, Math.floor(y / Math.max(1, rowH))));
  const r = rows[ri];
  const within = r.mids.findIndex((m) => x < m);
  if (within >= 0) return r.start + within;
  return ri + 1 < rows.length ? rows[ri + 1].start : boxes.length;   // past the row's last tab → the next row's head, or the very end
}
