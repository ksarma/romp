// The margin layout's pure half (plans/file-review.md, "The margin-layout follow-on (2026-09-07)"): the
// push-down rule over synthetic measurements. The DOM half (file-comments.ts, placeCards) is driven in
// file-comments-margin.test.ts and measured for real in file-comments-margin-browser.test.ts.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { layoutCards, CARD_GAP, type LayoutItem } from "./card-layout";

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

test("the input's order is not the placement order: cards are laid by desired top, a tie by the cards' fields and then the key, never by the input's order", () => {
  const r = layoutCards([{ key: "late", desired: 500, height: 30 }, { key: "early", desired: 50, height: 30 }, { key: "tie2", desired: 200, height: 30 }, { key: "tie1", desired: 200, height: 30 }], 8);
  assert.deepEqual(r.placed.map((p) => p.key), ["early", "tie1", "tie2", "late"], "desired order; the two bare items at 200 by key, though the input gives tie2 first");
  assert.deepEqual(tops(r), { early: 50, tie1: 200, tie2: 238, late: 500 });
});

// the tie rule (the Slice 4 review's round 16, 2026-09-10): the panel feeds the pass the model's order after a render and
// the last placement's order after any other pass, so a tie broken by the input's order laid the same cards differently
// from one pass to the next. The placement must be a function of the cards alone, and a tie lays in the list's order
// (the module comment; the review's round 1 ruling: a comment about a change lays after the change it is about).
const comment = (key: string, desired: number, height: number, ts: number): LayoutItem => ({ key, desired, height, kind: "comment", ts });
const change = (key: string, desired: number, height: number, from: number, ts: number): LayoutItem => ({ key, desired, height, kind: "change", from, ts });

test("the same cards in any input order place the same: a tie on the desired top lays the change card before the comment card, and the placement order fed back gives the placement again", () => {
  const a = comment("1757145570000-2", 200, 30, 1757145570000), b = change("chg:h1", 200, 50, 40, 1757145540000), c = comment("1757145600000-118", 400, 30, 1757145600000);
  const model = layoutCards([b, a, c], 8);           // the list's order: the change card first, then the comments by time
  const fed = layoutCards(model.placed.map((p) => [a, b, c].find((it) => it.key === p.key)!), 8);   // the placement order, as the next pass reads the DOM
  const other = layoutCards([a, b, c], 8);         // the comment before the change, as no list of the panel's gives them
  // without a focus the input's order was the placement's as first built too, so the read-back is a fixed point on the base
  // as well; the third order is the assertion that goes red there (the pair swapped)
  assert.deepEqual(fed, model, "the placement order read back places the same");
  assert.deepEqual(other, model, "and so does any other order (as first built, the tie followed the input: the pair swapped)");
  assert.deepEqual(model.placed.map((p) => p.key), ["chg:h1", "1757145570000-2", "1757145600000-118"], "the tie in the list's order: the change card before the comment card");
  assert.deepEqual(tops(model), { "chg:h1": 200, "1757145570000-2": 258, "1757145600000-118": 400 });
});

test("under a focus, the tied pair straddling the spill is laid the same by the model's order and by the placement order read back: no pass reverses it", () => {
  // the review's scene: a comment card (60) and a change card (67) whose marks share a line under the header, the focus a
  // little below with room above it for one of the two; as first built, each pass reversed the pair (the one at the start
  // spilled below the focus, the spilled one took the start) and the cards below moved by 7px every time
  const cmt = comment("1757145570000-2", -60, 60, 1757145570000), chg = change("chg:s1", -60, 67, 2, 1757145540000);
  const focus = comment("1757145600000-118", 100, 40, 1757145600000), below = comment("1757145630000-9", 900, 30, 1757145630000);
  const items = [cmt, chg, focus, below];
  const byKey = (r: ReturnType<typeof layoutCards>) => r.placed.map((p) => items.find((it) => it.key === p.key)!);
  const render = layoutCards([chg, cmt, focus, below], 8, focus.key);   // the render: the model's order, changes first
  const pass1 = layoutCards(byKey(render), 8, focus.key);              // the next pass: the DOM as the render's pass left it
  const pass2 = layoutCards(byKey(pass1), 8, focus.key);
  assert.deepEqual(pass1, render, "the pass over the placement order lays the same (as first built, the pair reversed at every pass)");
  assert.deepEqual(pass2, render, "and stays so");
  assert.deepEqual(layoutCards([below, focus, cmt, chg], 8, focus.key), render, "whatever order the cards come in");
  assert.deepEqual(tops(render), { "1757145570000-2": 8, "1757145600000-118": 100, "chg:s1": 148, "1757145630000-9": 900 }, "the change is first of the pair, so it is the one the chain has no room for: below the focus; the comment holds the start");
  assert.deepEqual(render.placed.map((p) => p.key), ["1757145570000-2", "1757145600000-118", "chg:s1", "1757145630000-9"]);
});

test("the focus on one of a tied pair: a same-line comment card keeps the list's side of a focused change card, below it, and a same-line change card lays above a focused comment card", () => {
  // the about follow-on lays a comment about a deletion at the change's own mark, so this tie is the ordinary case for such
  // a comment: the list shows the change first, and so does the margin, whichever of the two the person acted on
  const chg = change("chg:d1", 200, 50, 30, 1757145540000), cmt = comment("1757145570000-3", 200, 30, 1757145570000);
  const onChange = layoutCards([chg, cmt], 8, chg.key);
  assert.deepEqual(tops(onChange), { "chg:d1": 200, "1757145570000-3": 258 }, "the focused change at its mark, the comment below it (as first built, by key, the comment was pulled above it)");
  assert.deepEqual(layoutCards([cmt, chg], 8, chg.key), onChange, "whatever order the cards come in");
  const onComment = layoutCards([chg, cmt], 8, cmt.key);
  assert.deepEqual(tops(onComment), { "chg:d1": 142, "1757145570000-3": 200 }, "the focused comment at its mark, the change pulled up above it");
  assert.equal(onComment.placed.find((p) => p.key === "chg:d1")!.pushed, -58, "the change's leader down to the mark it left");
  assert.deepEqual(layoutCards([cmt, chg], 8, cmt.key), onComment, "whatever order the cards come in");
});

test("two change cards on one line lay by position then time, the list's order, and two comment cards by time: the key decides only what those leave tied", () => {
  // a later edit to the left of an earlier one: by key or by time the right-hand edit would come first, against the text's order
  const left = change("chg:b", 300, 30, 10, 1757145600000), right = change("chg:a", 300, 30, 40, 1757145500000);
  const r = layoutCards([right, left], 8);
  assert.deepEqual(r.placed.map((p) => p.key), ["chg:b", "chg:a"], "the left-hand edit first, though its key and its time come second (as first built, the input's order: chg:a first)");
  assert.deepEqual(layoutCards([left, right], 8), r, "whatever order the cards come in");
  // the same position (one insertion made twice at a point): by time
  const first = change("chg:z", 300, 30, 10, 1757145500000), second = change("chg:y", 300, 30, 10, 1757145600000);
  assert.deepEqual(layoutCards([second, first], 8).placed.map((p) => p.key), ["chg:z", "chg:y"], "the earlier edit first, though its key comes second");
  // two comments whose marks share a line: by time, whatever their ids
  const older = comment("1757145600000-9", 300, 30, 1757145500000), newer = comment("1757145500000-2", 300, 30, 1757145600000);
  assert.deepEqual(layoutCards([newer, older], 8).placed.map((p) => p.key), ["1757145600000-9", "1757145500000-2"], "the older comment first, though its key comes second");
  // the key last: two comments at one time
  const twin1 = comment("1757145600000-11", 300, 30, 1757145600000), twin2 = comment("1757145600000-2", 300, 30, 1757145600000);
  assert.deepEqual(layoutCards([twin2, twin1], 8).placed.map((p) => p.key), ["1757145600000-11", "1757145600000-2"]);
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
