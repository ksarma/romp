// The margin layout's pure half (plans/file-review.md, "The margin-layout follow-on (2026-09-07)"): the
// push-down rule over synthetic measurements. The DOM half (file-comments.ts, placeCards) is driven in
// file-comments-margin.test.ts and measured for real in file-comments-margin-browser.test.ts.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { layoutCards, CARD_GAP } from "./card-layout";

const web = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");

const tops = (r: ReturnType<typeof layoutCards>) => Object.fromEntries(r.placed.map((p) => [p.key, p.top]));

test("a card sits level with its mark when nothing is above it", () => {
  const r = layoutCards([{ key: "a", desired: 100, height: 40 }, { key: "b", desired: 300, height: 40 }], 8);
  assert.deepEqual(tops(r), { a: 100, b: 300 });
  assert.deepEqual(r.placed.map((p) => p.pushed), [0, 0]);
  assert.equal(r.bottom, 340);
});

test("push-down: a card whose mark is under the previous card is placed at that card's bottom plus the gap, never up", () => {
  const r = layoutCards([{ key: "a", desired: 100, height: 60 }, { key: "b", desired: 120, height: 40 }, { key: "c", desired: 400, height: 40 }], 8);
  assert.deepEqual(tops(r), { a: 100, b: 168, c: 400 });
  assert.equal(r.placed[1].pushed, 48, "how far b sits below its mark");
  assert.equal(r.placed[2].pushed, 0, "c is clear of the pushed card and sits level again");
});

test("the list's order is not the placement order: cards are laid by desired top, ties by the list's order", () => {
  const r = layoutCards([{ key: "late", desired: 500, height: 30 }, { key: "early", desired: 50, height: 30 }, { key: "tie2", desired: 200, height: 30 }, { key: "tie1", desired: 200, height: 30 }], 8);
  assert.deepEqual(r.placed.map((p) => p.key), ["early", "tie2", "tie1", "late"], "desired order; the two at 200 keep the list's order");
  assert.deepEqual(tops(r), { early: 50, tie2: 200, tie1: 238, late: 500 });
});

test("the gap is the caller's, and the sheet's card gap is the module's default", () => {
  const r = layoutCards([{ key: "a", desired: 100, height: 10 }, { key: "b", desired: 100, height: 10 }], 20);
  assert.deepEqual(tops(r), { a: 100, b: 130 });
  assert.equal(CARD_GAP, 8);
  assert.match(web("styles.css"), /\.fc-cards \{ display: flex; flex-direction: column; gap: 8px; \}/, "the list's gap in the sheet is the default gap here");
  const d = layoutCards([{ key: "a", desired: 100, height: 10 }, { key: "b", desired: 100, height: 10 }]);
  assert.deepEqual(tops(d), { a: 100, b: 118 });
});

test("the loose group: cards with no mark stack at the top of the track in the list's order, and the placed cards begin below it", () => {
  const r = layoutCards([
    { key: "whole", desired: null, height: 30 }, { key: "a", desired: 10, height: 40 }, { key: "detached", desired: null, height: 30 }, { key: "b", desired: 300, height: 40 },
  ], 8);
  assert.deepEqual(r.placed.map((p) => p.key), ["whole", "detached", "a", "b"], "loose first, in the list's order, then the marked cards");
  assert.deepEqual(tops(r), { whole: 8, detached: 46, a: 84, b: 300 });
  assert.equal(r.placed[2].pushed, 74, "a's mark is under the loose group: pushed, like any collision");
  assert.deepEqual(r.placed.filter((p) => p.desired === null).map((p) => p.pushed), [0, 0], "a loose card is never 'pushed': it has no mark to sit level with");
});

test("an expanded card pushes the cards below it: the same marks, one taller card, the next card moves down by the growth", () => {
  const closed = layoutCards([{ key: "a", desired: 100, height: 40 }, { key: "b", desired: 130, height: 40 }, { key: "c", desired: 400, height: 40 }], 8);
  const open = layoutCards([{ key: "a", desired: 100, height: 200 }, { key: "b", desired: 130, height: 40 }, { key: "c", desired: 400, height: 40 }], 8);
  assert.equal(tops(closed).b, 148, "b's mark is 30px under a's card: pushed to a's bottom plus the gap");
  assert.equal(tops(open).b, 308, "b follows a's new bottom");
  assert.equal(tops(open).c, 400, "c was clear of both and does not move: a card moves only when a card above it reaches it");
  assert.equal(open.bottom, 440);
});

test("a mark above the track's origin (desired negative: the header stands over it) is clamped to the top inset, and the track's bottom follows the last card", () => {
  const r = layoutCards([{ key: "a", desired: -40, height: 30 }], 8);
  assert.deepEqual(tops(r), { a: 8 });
  assert.equal(r.placed[0].pushed, 48);
  assert.equal(r.bottom, 38);
  assert.deepEqual(layoutCards([], 8), { placed: [], bottom: 0 });
});

// ── the focus (the focus follow-on, 2026-09-08): the focused card at its mark, the cards above moved up only as needed ──

test("the focus: a tall card above a passage no longer pushes the passage's card down — the focused card sits at its mark, and the tall card moves up by the least that clears it", () => {
  const items = [{ key: "tall", desired: 100, height: 500 }, { key: "c", desired: 600, height: 60 }];
  const plain = layoutCards(items, 8);
  assert.deepEqual(tops(plain), { tall: 100, c: 608 }, "without a focus the push-down rule: the comment's card a card's height below its mark");
  const r = layoutCards(items, 8, "c");
  assert.deepEqual(tops(r), { tall: 92, c: 600 });
  assert.equal(r.placed.find((p) => p.key === "c")!.pushed, 0, "the focused card is level");
  assert.equal(r.placed.find((p) => p.key === "tall")!.pushed, -8, "the moved card's push is negative: how far above its mark it sits");
  assert.deepEqual(r.placed.map((p) => p.key), ["tall", "c"], "placement order is still top to bottom");
  assert.equal(r.bottom, 660);
  // the tall card moves up only as far as the track's start lets it: where the focused card's mark is nearer the start than
  // the tall card is tall, the card goes BELOW the focused card instead of past the start (the follow-on's review,
  // 2026-09-08; card-layout-reach.test.ts has the rule's cases)
  const near = layoutCards([{ key: "tall", desired: 100, height: 500 }, { key: "c", desired: 300, height: 60 }], 8, "c");
  assert.deepEqual(tops(near), { c: 300, tall: 368 }, "(as first built: tall at -208, its head 208px above the start)");
  assert.ok(near.placed.every((p) => p.top >= 0), "no card past the start");
});

test("the focus: cards above shift up only as much as needed — a card clear of the focused card stays put, a pushed one keeps its push where it fits", () => {
  // a at 100 (h 60) pushes b (mark 120) to 168; the focus f at 400 is far below: nothing above it moves
  const far = layoutCards([{ key: "a", desired: 100, height: 60 }, { key: "b", desired: 120, height: 40 }, { key: "f", desired: 400, height: 40 }], 8, "f");
  assert.deepEqual(tops(far), { a: 100, b: 168, f: 400 }, "the old result: no card above met the focus");
  // f at 200: b (168..208) overlaps it and moves up to 152, still 32 under its mark; a (100..160) now runs under b and gives
  // the 16 that clears it, no more
  const nearer = layoutCards([{ key: "a", desired: 100, height: 60 }, { key: "b", desired: 120, height: 40 }, { key: "f", desired: 200, height: 40 }], 8, "f");
  assert.deepEqual(tops(nearer), { a: 84, b: 152, f: 200 });
  assert.deepEqual(nearer.placed.map((p) => p.pushed), [-16, 32, 0], "b still sits under its mark, by less; a is 16 above its own");
  // f at 150: b moves to 102 and a must give way too, to 34
  const chain = layoutCards([{ key: "a", desired: 100, height: 60 }, { key: "b", desired: 120, height: 40 }, { key: "f", desired: 150, height: 40 }], 8, "f");
  assert.deepEqual(tops(chain), { a: 34, b: 102, f: 150 });
  assert.deepEqual(chain.placed.map((p) => p.pushed), [-66, -18, 0]);
});

test("the focus: the cards below it are laid as always — the push-down rule from the focused card's bottom", () => {
  const r = layoutCards([{ key: "f", desired: 100, height: 200 }, { key: "b", desired: 150, height: 40 }, { key: "c", desired: 400, height: 40 }], 8, "f");
  assert.deepEqual(tops(r), { f: 100, b: 308, c: 400 });
  assert.equal(r.placed[1].pushed, 158);
  const plain = layoutCards([{ key: "f", desired: 100, height: 200 }, { key: "b", desired: 150, height: 40 }, { key: "c", desired: 400, height: 40 }], 8);
  assert.deepEqual(tops(plain), tops(r), "the first card as the focus is the old result: nothing stands above it");
});

test("the focus and the loose group: the group stays at the top until the moved cards reach it, then moves up with them as far as the track's start — never past it: a card the chain cannot fit above the focus goes below it", () => {
  const loose = [{ key: "whole", desired: null, height: 30 }, { key: "detached", desired: null, height: 30 }];   // 8..38, 46..76; the marked cards begin at 84
  // the focus far below: the group stays
  const far = layoutCards([...loose, { key: "a", desired: 100, height: 40 }, { key: "f", desired: 400, height: 40 }], 8, "f");
  assert.deepEqual(tops(far), { whole: 8, detached: 46, a: 100, f: 400 });
  // room for the chain at the start: a (100..140) meets f at 130: a to 82, the group's end 76 + 8 = 84 > 82: the group moves up 2, to 6
  const room = layoutCards([...loose, { key: "a", desired: 100, height: 40 }, { key: "f", desired: 130, height: 40 }], 8, "f");
  assert.deepEqual(tops(room), { whole: 6, detached: 44, a: 82, f: 130 });
  // a (100..140) meets f at 120: a moves up to 72, which reaches the group's end (76 + gap) and asks it for 12 — 4 more than the
  // start allows. The group is not moved past the start (the follow-on's review, 2026-09-08: a card at a negative top could be
  // neither read nor reached): the card at its end goes below the focused card, in the list's order, and the rest stays
  const met = layoutCards([...loose, { key: "a", desired: 100, height: 40 }, { key: "f", desired: 120, height: 40 }], 8, "f");
  assert.deepEqual(tops(met), { whole: 8, a: 72, f: 120, detached: 168 }, "(as first built: whole at -4, past the start)");
  assert.deepEqual(met.placed.map((p) => p.key), ["whole", "a", "f", "detached"], "placement order is top to bottom, the displaced card after the focus");
  // a tall card above the focus that the start leaves no room for: it goes below the focused card, wearing the leader up to
  // its mark, and the group above never moved
  const tall = layoutCards([...loose, { key: "a", desired: 100, height: 300 }, { key: "f", desired: 120, height: 40 }], 8, "f");
  assert.deepEqual(tops(tall), { whole: 8, detached: 46, f: 120, a: 168 }, "(as first built: -264, -226, -188 — three cards above the start)");
  assert.equal(tall.placed.find((p) => p.key === "a")!.pushed, 68, "the displaced card's leader up to its mark");
  assert.deepEqual(tall.placed.filter((p) => p.desired === null).map((p) => p.pushed), [0, 0], "a loose card is never 'pushed', moved or not");
  assert.deepEqual(tall.placed.map((p) => p.key), ["whole", "detached", "f", "a"], "placement order: the group, the focus, the card it displaced");
});

test("the focus: no focus, a focus with no mark and an unknown focus each give the old result; a focused mark under the header is clamped to the top inset like any first card", () => {
  const items = [{ key: "whole", desired: null, height: 30 }, { key: "a", desired: 100, height: 60 }, { key: "b", desired: 120, height: 40 }];
  const plain = layoutCards(items, 8);
  assert.deepEqual(layoutCards(items, 8, null), plain);
  assert.deepEqual(layoutCards(items, 8, "whole"), plain, "a loose card has no mark to sit level with: the old result");
  assert.deepEqual(layoutCards(items, 8, "nobody"), plain, "a key not among the items: the old result");
  assert.deepEqual(layoutCards(items), plain, "the default is no focus");
  const under = layoutCards([{ key: "a", desired: -40, height: 30 }, { key: "b", desired: 10, height: 30 }], 8, "a");
  assert.deepEqual(tops(under), { a: 8, b: 46 });
  assert.equal(under.placed[0].pushed, 48, "clamped to the inset, as without a focus");
});
