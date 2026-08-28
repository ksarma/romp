// Executable geometry for the drag-flap fix (2026-08-28): the slot the provisional tab lands in
// is computed against a VIRTUAL wrap layout of the non-dragged tabs — boundaries that cannot move
// in response to the insert they cause, so monotone pointer motion gives monotone slots and the
// oscillation in the user's recording is impossible by construction.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { dragSlotIndex, type SlotBox } from "./dragslot";

const boxes = (...w: number[]): SlotBox[] => w.map((x, i) => ({ id: "t" + i, w: x }));

test("a smooth leftward sweep crosses each boundary once — slots are monotone, never oscillating", () => {
  // variable widths on a wrapping strip: 3 rows at 300px
  const b = boxes(120, 90, 140, 60, 110, 100, 80);
  let prev = Infinity;
  for (let x = 299; x >= 0; x -= 3) {
    const idx = dragSlotIndex(b, 300, 0, 30, x, 45);   // sweeping row 2 (y=45, rowH=30)
    assert.ok(idx <= prev, `monotone under monotone motion (x=${x}: ${idx} > ${prev})`);
    prev = idx;
  }
});

test("rows resolve by y band; within a row the midpoints decide", () => {
  const b = boxes(100, 100, 100, 100);   // 2 per 250px row
  assert.equal(dragSlotIndex(b, 250, 0, 30, 40, 10), 0, "row 1, left of t0's midpoint");
  assert.equal(dragSlotIndex(b, 250, 0, 30, 60, 10), 1, "row 1, past t0's midpoint");
  assert.equal(dragSlotIndex(b, 250, 0, 30, 40, 40), 2, "row 2 by y band");
  assert.equal(dragSlotIndex(b, 250, 0, 30, 160, 40), 4, "past row 2's last midpoint → the end");
});

test("past a row's tabs lands at the next row's head; beyond every row lands at the end", () => {
  const b = boxes(200, 200, 200);        // one per 250px row
  assert.equal(dragSlotIndex(b, 250, 0, 30, 240, 5), 1, "right of row 1's tab → row 2's head");
  assert.equal(dragSlotIndex(b, 250, 0, 30, 99, 900), 2, "y clamps to the last row");
  assert.equal(dragSlotIndex(b, 250, 0, 30, 240, 900), 3, "…and past its midline is the very end");
});

test("the gap participates in the layout (the Yatharth strip's 3px seam)", () => {
  const b = boxes(120, 120);             // 120+3+120 = 243 > 240 → wraps
  assert.equal(dragSlotIndex(b, 240, 3, 30, 10, 40), 1, "the second tab wrapped to row 2");
});

test("degenerate inputs stay sane", () => {
  assert.equal(dragSlotIndex([], 300, 0, 30, 50, 50), 0);
  assert.equal(dragSlotIndex(boxes(400), 300, 0, 30, 10, -20), 0, "negative y clamps to row 0");
});
