// Every card the layout places can be reached (the focus follow-on's review, 2026-09-08). The focus rule
// (card-layout.ts, the module comment; card-layout.test.ts drives the rest of it) moved the cards above the focused
// card up the track by the least that cleared it — and, as first built, past the track's start when they did not fit
// between the start and the focus. A card at a negative top was neither readable nor reachable: the track cannot
// scroll above 0, a card's head is its only control, a loose card has no mark to click, and the placement held across
// every pass until some other gesture changed the focus. The common gesture tripped it: with a whole-file comment in
// the store, a click on the first paragraph's highlight put the comment's card at the top inset and the whole-file
// card wholly above the start, gone from the panel while the header still counted it. Now a card the chain would move
// past the start is laid below the focused card instead, by the push-down rule from its end: the marked ones first,
// wearing the leader up to their marks, then the loose ones in the list's order, then the cards whose marks are below
// the focus. The room above the focus stays for the cards further up the chain, and of the loose group the cards at
// its end go below until the rest fit, so the group's head keeps its place at the start. Synthetic measurements only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { layoutCards, type LayoutItem, type Layout } from "./card-layout";

const tops = (r: Layout) => Object.fromEntries(r.placed.map((p) => [p.key, p.top]));
const pushed = (r: Layout) => Object.fromEntries(r.placed.map((p) => [p.key, p.pushed]));
const order = (r: Layout) => r.placed.map((p) => p.key);

test("the review's scene: a whole-file comment and a comment on the first paragraph — the first paragraph's card as the focus sits at the top inset, and the whole-file card stands below it, not above the start", () => {
  const items: LayoutItem[] = [{ key: "whole", desired: null, height: 60 }, { key: "first", desired: 4, height: 60 }];
  const plain = layoutCards(items, 8);
  assert.deepEqual(tops(plain), { whole: 8, first: 76 }, "without a focus the loose group at the top and the first paragraph's card pushed under it, as ever");
  const r = layoutCards(items, 8, "first");
  assert.deepEqual(tops(r), { first: 8, whole: 76 }, "the focused card at the inset (its mark is under the header); the whole-file card below it, where a scroll reaches it (as first built: -60, nothing of it in the track)");
  assert.deepEqual(order(r), ["first", "whole"], "placement order is top to bottom");
  assert.deepEqual(pushed(r), { first: 4, whole: 0 }, "the clamp's push on the focused card; a loose card is never pushed");
  assert.equal(r.bottom, 136);
  // the same with a change the view does not paint (loose) above a focused change card whose mark is near the top
  const chg = layoutCards([{ key: "whole", desired: null, height: 60 }, { key: "chg:h1", desired: 20, height: 100 }], 8, "chg:h1");
  assert.deepEqual(tops(chg), { "chg:h1": 20, whole: 128 }, "(as first built: whole at -48)");
});

test("a card the chain cannot fit above the focus goes below it, wearing the leader up to its mark: the tall change card of the follow-on's own scene, when the passage's mark is nearer the start than the card is tall", () => {
  const items: LayoutItem[] = [{ key: "tall", desired: 100, height: 500 }, { key: "c", desired: 300, height: 60 }];
  const r = layoutCards(items, 8, "c");
  assert.deepEqual(tops(r), { c: 300, tall: 368 }, "the focused card level; the tall card below it (as first built: -208, its head 216px above the start)");
  assert.deepEqual(order(r), ["c", "tall"]);
  assert.equal(r.placed.find((p) => p.key === "c")!.pushed, 0, "the focused card is level");
  assert.equal(r.placed.find((p) => p.key === "tall")!.pushed, 268, "a pushed card: the leader up to its mark, as any card under another draws it");
  assert.equal(r.bottom, 868, "the track's content reaches the moved card");
  // with room above, the card moves up as before: the mark at 600, the tall card (100..600) ends a gap above it
  const room = layoutCards([{ key: "tall", desired: 100, height: 500 }, { key: "c", desired: 600, height: 60 }], 8, "c");
  assert.deepEqual(tops(room), { tall: 92, c: 600 }, "the chain's move up, unchanged where the card fits above the focus");
  assert.equal(room.placed[0].pushed, -8, "8px above its mark: the least that clears the focused card");
});

test("the room above the focus stays for the cards further up the chain: a small card above a tall one that did not fit keeps its place, and so does the loose group under a ceiling it fits", () => {
  // a1 fits above f, a2 (400 tall, its mark 300px above f's) does not: a2 alone goes below
  const r = layoutCards([{ key: "a1", desired: 50, height: 40 }, { key: "a2", desired: 100, height: 400 }, { key: "f", desired: 400, height: 40 }], 8, "f");
  assert.deepEqual(tops(r), { a1: 50, f: 400, a2: 448 });
  assert.deepEqual(order(r), ["a1", "f", "a2"]);
  assert.deepEqual(pushed(r), { a1: 0, f: 0, a2: 348 }, "a1 never met the focus and is level; a2 sits under its mark by the push");
  // the loose group under a tall card that spills: the group never moved (as first built: whole -264, detached -226, a -188)
  const loose = [{ key: "whole", desired: null, height: 30 }, { key: "detached", desired: null, height: 30 }];
  const tall = layoutCards([...loose, { key: "a", desired: 100, height: 300 }, { key: "f", desired: 120, height: 40 }], 8, "f");
  assert.deepEqual(tops(tall), { whole: 8, detached: 46, f: 120, a: 168 });
  assert.deepEqual(order(tall), ["whole", "detached", "f", "a"], "the group, the focus, then the card it displaced");
  assert.deepEqual(tall.placed.filter((p) => p.desired === null).map((p) => p.pushed), [0, 0], "a loose card is never 'pushed'");
  assert.equal(tall.placed.find((p) => p.key === "a")!.pushed, 68);
});

test("the loose group moves up as one, as far as the track's start; past that, the cards at its end go below the focus in the list's order, so the group's head stays at the start", () => {
  const loose = [{ key: "whole", desired: null, height: 30 }, { key: "detached", desired: null, height: 30 }];   // 8..38, 46..76
  // a (100..140) meets f at 124: a to 76, the group's end 76 needs 8 more: the group to the start exactly
  const start = layoutCards([...loose, { key: "a", desired: 100, height: 40 }, { key: "f", desired: 124, height: 40 }], 8, "f");
  assert.deepEqual(tops(start), { whole: 0, detached: 38, a: 76, f: 124 }, "the first loose card at 0: the start, not past it");
  // one pixel less room: the group cannot fit whole; its last card goes below the focus and the rest stays where it was
  const past = layoutCards([...loose, { key: "a", desired: 100, height: 40 }, { key: "f", desired: 123, height: 40 }], 8, "f");
  assert.deepEqual(tops(past), { whole: 8, a: 75, f: 123, detached: 171 }, "(as first built: whole at -1)");
  assert.deepEqual(order(past), ["whole", "a", "f", "detached"]);
  assert.deepEqual(pushed(past), { whole: 0, a: -25, f: 0, detached: 0 });
  // three loose cards over a focus near the top: the head of the group stays, the two after it go below in the list's order
  const three = layoutCards([{ key: "l1", desired: null, height: 60 }, { key: "l2", desired: null, height: 60 }, { key: "l3", desired: null, height: 60 }, { key: "f", desired: 120, height: 40 }], 8, "f");
  assert.deepEqual(tops(three), { l1: 8, f: 120, l2: 168, l3: 236 }, "(as first built: -84, -16, 52)");
  assert.deepEqual(order(three), ["l1", "f", "l2", "l3"], "the list's order, read down the track, with the focus between");
});

test("the displaced cards below the focus: the marked ones first, then the loose ones, and the cards whose marks are below the focus follow from the last of them", () => {
  const items: LayoutItem[] = [
    { key: "whole", desired: null, height: 60 }, { key: "a", desired: 10, height: 40 }, { key: "f", desired: 30, height: 40 }, { key: "b", desired: 150, height: 40 }, { key: "c", desired: 400, height: 40 },
  ];
  const r = layoutCards(items, 8, "f");
  assert.deepEqual(tops(r), { f: 30, a: 78, whole: 126, b: 194, c: 400 });
  assert.deepEqual(order(r), ["f", "a", "whole", "b", "c"]);
  assert.deepEqual(pushed(r), { f: 0, a: 68, whole: 0, b: 44, c: 0 }, "a and b pushed under the cards above them; c clear of them all and level");
  assert.equal(r.bottom, 440);
});

test("every card the focus rule places stands at or below the track's start, cards never overlap, the focused card is at its mark, and the loose group keeps the list's order — over a grid of fixtures", () => {
  const heights = [30, 60, 200], marks = [4, 40, 120, 300];
  let cases = 0;
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
      for (const p of r.placed) assert.equal(p.pushed, p.desired === null ? 0 : p.top - p.desired, "pushed is the card's distance under its mark" + where);
      assert.equal(r.bottom, Math.max(...r.placed.map((p) => p.top + p.height)), "the bottom is the last card's end" + where);
      const looseOrder = order(r).filter((k) => k.startsWith("loose"));
      assert.deepEqual(looseOrder, items.filter((it) => it.desired === null).map((it) => it.key), "the loose group in the list's order, above or below the focus" + where);
    }
  }
  assert.ok(cases > 1000, "the grid is not trivial: " + cases);
});
