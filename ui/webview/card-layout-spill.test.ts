// A card laid below the focus stands above nothing (the focus follow-on's verification round, 2026-09-09). The reach
// rule (card-layout-reach.test.ts) lays a card the chain would move past the track's start below the focused card
// instead — but the pass ran once, so a card BETWEEN that card and the focus kept the push the spilled card had given
// it in the push-down layout: it sat under its mark wearing a leader up a gutter no card stood in. In the panel's own
// stand-in scene (file-comments-focus.test.ts's world: the whole-file card, the heading's, the passage's, an essay and
// a change card shown whole) the passage's card stood 72px under its mark with 212px of empty track above it, its
// leader claiming a push the change card, by then below the essay, no longer made. Now the pass runs again without the
// cards it laid below, until a pass moves no card past the start: the card between is laid from its own mark, and the
// card under a spilled whole-file card takes the start the group gave up. Synthetic measurements only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { layoutCards, type LayoutItem, type Layout } from "./card-layout";

const tops = (r: Layout) => Object.fromEntries(r.placed.map((p) => [p.key, p.top]));
const pushed = (r: Layout) => Object.fromEntries(r.placed.map((p) => [p.key, p.pushed]));
const order = (r: Layout) => r.placed.map((p) => p.key);

test("the card between a spilled tall card and the focus is laid from its own mark, not from the push the spilled card gave it", () => {
  // A (100..340) pushes B (mark 130) to 348 in the push-down layout; the focus F at 300 leaves A no room above (300 - 8 - 240 < 0)
  const items: LayoutItem[] = [{ key: "A", desired: 100, height: 240 }, { key: "B", desired: 130, height: 60 }, { key: "F", desired: 300, height: 60 }];
  const r = layoutCards(items, 8, "F");
  assert.deepEqual(tops(r), { B: 130, F: 300, A: 368 }, "B level with its mark (laid once: 232, 102px under it with the track empty above); A below the focus");
  assert.deepEqual(pushed(r), { B: 0, F: 0, A: 268 }, "no leader on B; A's leader up to its mark, as any card under another draws it");
  assert.deepEqual(order(r), ["B", "F", "A"]);
  assert.equal(r.bottom, 608);
  // with A never there the layout is the same for B and F: the spilled card has no say above the focus
  const without = layoutCards(items.filter((it) => it.key !== "A"), 8, "F");
  assert.deepEqual(tops(without), { B: 130, F: 300 });
});

test("two cards between the spilled card and the focus: the first at its mark, the second pushed only by the first", () => {
  const r = layoutCards([{ key: "A", desired: 100, height: 240 }, { key: "B", desired: 130, height: 60 }, { key: "C", desired: 160, height: 60 }, { key: "F", desired: 300, height: 60 }], 8, "F");
  assert.deepEqual(tops(r), { B: 130, C: 198, F: 300, A: 368 }, "(laid once: B 164, C 232 — stacked tight over the focus with the track empty above)");
  assert.deepEqual(pushed(r), { B: 0, C: 38, F: 0, A: 268 }, "C's push is B's doing: B ends a gap above it");
});

test("a card above the spilled one still pushes the card between: the push that stands is the one a card above it makes", () => {
  // Z (20..130) is above A in the push-down layout and stays above the focus; B's mark at 130 is under Z's end
  const r = layoutCards([{ key: "Z", desired: 20, height: 110 }, { key: "A", desired: 100, height: 240 }, { key: "B", desired: 130, height: 60 }, { key: "F", desired: 300, height: 60 }], 8, "F");
  assert.deepEqual(tops(r), { Z: 20, B: 138, F: 300, A: 368 });
  assert.deepEqual(pushed(r), { Z: 0, B: 8, F: 0, A: 268 }, "B sits a gap under Z, the card that is above it; nothing of A's push remains");
  // a small card above the tall one keeps its place (the reach rule) and the card between is level, together
  const small = layoutCards([{ key: "C", desired: 20, height: 60 }, { key: "A", desired: 100, height: 240 }, { key: "B", desired: 130, height: 60 }, { key: "F", desired: 300, height: 60 }], 8, "F");
  assert.deepEqual(tops(small), { C: 20, B: 130, F: 300, A: 368 });
  assert.deepEqual(pushed(small), { C: 0, B: 0, F: 0, A: 268 });
});

test("the loose group's spill: the first paragraph's card takes the start a spilled whole-file card gave up", () => {
  // the reach rule's own scene with a tall whole-file card: it goes below the focus; laid once, m1 kept the push the
  // group had given it (82, 78px under its mark, rows 8..74 empty)
  const r = layoutCards([{ key: "whole", desired: null, height: 200 }, { key: "m1", desired: 4, height: 30 }, { key: "m2", desired: 120, height: 60 }], 8, "m2");
  assert.deepEqual(tops(r), { m1: 8, m2: 120, whole: 188 }, "m1 at the inset (its mark is under the header); the whole-file card below the focus");
  assert.deepEqual(pushed(r), { m1: 4, m2: 0, whole: 0 }, "the clamp's push alone on m1; a loose card is never pushed");
  assert.deepEqual(order(r), ["m1", "m2", "whole"]);
  // the group's head kept and its end spilled: the card under the group is laid from the kept head's end, not the whole group's
  const two = layoutCards([{ key: "l1", desired: null, height: 60 }, { key: "l2", desired: null, height: 60 }, { key: "m1", desired: 100, height: 30 }, { key: "m2", desired: 160, height: 40 }], 8, "m2");
  assert.deepEqual(tops(two), { l1: 8, m1: 100, m2: 160, l2: 208 }, "l1 (8..68) leaves m1 its mark; laid once m1 stood at 122, under l2's old end");
  assert.deepEqual(pushed(two), { l1: 0, m1: 0, m2: 0, l2: 0 });
});

test("over a grid of fixtures: every pushed card sits a gap under the card placed above it — no leader claims a push no card makes — and the reach rule's invariants hold", () => {
  const heights = [30, 60, 240], marks = [4, 40, 130, 300];
  let cases = 0, spills = 0;
  for (const looseN of [0, 1, 2]) for (const h1 of heights) for (const h2 of heights) for (const m1 of marks) for (const m2 of marks) for (const hl of heights) {
    const items: LayoutItem[] = [];
    for (let i = 0; i < looseN; i++) items.push({ key: "loose" + i, desired: null, height: hl });
    items.push({ key: "m1", desired: m1, height: h1 }, { key: "m2", desired: m2, height: h2 }, { key: "m3", desired: 600, height: 40 });
    for (const focus of ["m1", "m2", "m3"]) {
      const r = layoutCards(items, 8, focus);
      const where = " in " + JSON.stringify(items) + " focus " + focus;
      cases++;
      assert.deepEqual(order(r).sort(), items.map((it) => it.key).sort(), "every item placed once" + where);
      for (const p of r.placed) assert.ok(p.top >= 0, p.key + " at " + p.top + ": above the start" + where);
      for (let i = 1; i < r.placed.length; i++) assert.ok(r.placed[i].top >= r.placed[i - 1].top + r.placed[i - 1].height + 8, "placed top to bottom, a gap between" + where);
      const f = r.placed.find((p) => p.key === focus)!;
      assert.equal(f.top, Math.max(f.desired as number, 8), "the focused card at its mark (clamped to the inset)" + where);
      // the invariant this module is for: a card under its mark (past the inset's clamp) is under the card placed above it
      // by exactly the gap, and the first card placed is never under its mark
      r.placed.forEach((p, i) => {
        if (p.desired === null || p.top <= Math.max(p.desired, 8)) return;
        assert.ok(i > 0, p.key + " is pushed to " + p.top + " with nothing above it" + where);
        assert.equal(p.top, r.placed[i - 1].top + r.placed[i - 1].height + 8, p.key + " is pushed to " + p.top + " by no card: the card above it ends at " + (r.placed[i - 1].top + r.placed[i - 1].height) + where);
      });
      // a spill: a card whose mark is above the focus placed after it, or a loose card placed after the focus
      const fi = order(r).indexOf(focus);
      if (r.placed.slice(fi + 1).some((p) => p.desired === null || (p.desired as number) < (f.desired as number) || ((p.desired as number) === f.desired && items.findIndex((it) => it.key === p.key) < items.findIndex((it) => it.key === focus)))) spills++;
    }
  }
  assert.ok(cases > 1000, "the grid is not trivial: " + cases);
  assert.ok(spills > 100, "the grid exercises the spill: " + spills + " of " + cases);
});
