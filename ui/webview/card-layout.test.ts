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
