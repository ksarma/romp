// The chat window's two height figures, executed (turn-estimate.ts; PR E, 2026-09-19). The head gap's per-turn estimate is
// the median over the turns the window holds whole (a visible user row to the next), never the window's height over its
// user-row count: that old figure, measured once for the view's life, read about 7,150 px per turn off a tail window with
// one user row and 79 dense rows and drew a 200-turn head gap at 1.43M px on the paint after the first. render.ts
// measureUnits feeds these off the unit observer's border-box heights (spacer-measure.test.ts drives that seam).
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { completeTurnHeights, isSpacerRow, isTurnRow, isUserRow, meanRowHeight, median, MIN_COMPLETE_TURNS, perTurnEstimate, rowsFor, type EstRow } from "./turn-estimate";
import { DEFAULT_TURN_PX, MAX_TURN_PX, gapHeight } from "./chat-regions";

const row = (cls: string, h: number | undefined, hidden = false): EstRow => ({ cls, hidden, h });
const user = (h: number | undefined = 30) => row("turn turn-user", h);
const asst = (h: number | undefined) => row("turn turn-assistant", h);
const tool = (h: number | undefined) => row("turn turn-tool", h);
const sum = (rows: EstRow[]) => rows.reduce((a, r) => a + (r.h ?? 0), 0);

test("a window with one leading partial turn and two complete turns measures the median of the complete turns, never the window's height per user row", () => {
  // the shape the phone had: dense rows of a turn whose prompt is above the window, then two whole turns, then the turn streaming
  const rows = [asst(500), tool(500), asst(500), user(30), asst(70), user(30), asst(90), user(30), asst(900)];
  assert.deepEqual(completeTurnHeights(rows), [100, 120], "the two turns between three visible user rows");
  assert.equal(perTurnEstimate(rows), 100, "the lower of the two: a height a turn in the window has");
  const users = rows.filter(isUserRow).length;
  assert.equal(users, 3);
  assert.notEqual(perTurnEstimate(rows), sum(rows) / users, "the old figure: every row over the user-row count (" + sum(rows) / users + ")");
  assert.ok(perTurnEstimate(rows)! < sum(rows) / 10, "an order of magnitude under the window's height");
});

test("fewer than two complete turns yields no figure: one user row (no complete turn), or exactly one complete turn", () => {
  assert.equal(MIN_COMPLETE_TURNS, 2);
  const oneUser = [asst(90), user(40), ...Array.from({ length: 78 }, () => asst(90))];   // the phone's tail window: 80 rows, one prompt
  assert.deepEqual(completeTurnHeights(oneUser), []);
  assert.equal(perTurnEstimate(oneUser), null, "no complete turn: the caller keeps what it had (the default until a window has two)");
  const oneTurn = [user(30), asst(70), user(30), asst(900)];
  assert.deepEqual(completeTurnHeights(oneTurn), [100]);
  assert.equal(perTurnEstimate(oneTurn), null, "one complete turn is not enough");
  assert.equal(perTurnEstimate([]), null);
  assert.equal(perTurnEstimate([user(30), asst(70), user(30), asst(50), user(30)]), 80, "two complete turns (100 and 80): the lower, never their mean (90 is a height no turn has)");
});

test("the figure is whole pixels: sub-pixel layout differences between two windows of the same turns are not a change", () => {
  // rows lay out at fractions of a pixel (a 27.09375 px row was read in the landing lab); over a 200-turn gap a thirty-second of a pixel
  // per turn is 7 px of spacer movement to compensate for nothing
  const a = [user(30.03125), asst(70.0625), user(30), asst(90.03125), user(30), asst(900)];
  const b = [user(30), asst(70), user(30.09375), asst(90), user(30), asst(900)];
  assert.equal(perTurnEstimate(a), 100); assert.equal(perTurnEstimate(b), 100);
  assert.equal(median([100.09375, 120.03125]), 100.09375, "the median itself keeps the fraction; the figure rounds it");
  assert.equal(perTurnEstimate([user(30), asst(70.6), user(30), asst(70.6), user(30)]), 101, "…to the nearest pixel");
});

test("the trailing turn is the one streaming and is never counted, so a growing reply moves no figure", () => {
  const rows = [user(30), asst(70), user(30), asst(90), user(30), asst(100)];
  const before = perTurnEstimate(rows);
  rows[5] = asst(5000);
  assert.equal(perTurnEstimate(rows), before, "the last turn grew by 4,900 px and the figure stood");
  assert.equal(before, 100);
});

test("a hidden user row (a stripped record, the echo of a send) starts no turn: a long turn holding one stays one turn", () => {
  const stripped = row("turn turn-user turn-user-empty", undefined, true), echo = row("turn turn-user turn-echo-hidden", 0, true);
  assert.ok(!isUserRow(stripped) && !isUserRow(echo) && isTurnRow(stripped), "hidden user rows are turn rows that start nothing");
  const rows = [user(30), asst(100), stripped, tool(50), echo, asst(100), user(30), asst(40), user(30), asst(900)];
  assert.deepEqual(completeTurnHeights(rows), [280, 70], "one turn of 280 px, not two turns split at the hidden rows");
  assert.equal(perTurnEstimate(rows), 70);
});

test("a window whose rows all report 0 (the view has no box: an ancestor hid it) yields no figure, never 0", () => {
  // the ancestor-hide shape (the author's pass 0, high): Chromium delivers every unit at 0 with the view at width 0; read as heights, three
  // complete turns of 0 px gave a median of 0, a figure applyMeasure takes (0 is neither null nor the old figure) and gapHeight draws
  // every gap at 0 px with. The rule is meanRowHeight's `h > 0`, the one the old estimator kept: a positive figure or none
  const zeros = [asst(0), user(0), asst(0), tool(0), user(0), asst(0), user(0), asst(0), user(0), asst(0)];
  assert.deepEqual(completeTurnHeights(zeros), [0, 0, 0], "three complete turns, none with a height");
  assert.equal(median([0, 0, 0]), 0, "their median is 0…");
  assert.equal(perTurnEstimate(zeros), null, "…and the estimate refuses it: no figure, the caller keeps what it had");
  assert.notEqual(perTurnEstimate(zeros), 0, "never 0");
  assert.equal(gapHeight({ lo: 0, hi: 200 }, 0), 0, "what a 0 figure would have drawn: every gap at 0 px (the estimator never hands one out)");
  assert.equal(meanRowHeight(zeros), null, "the average refuses a population of zeros the same way");
  // a zero turn among measured ones: the median stands on the measured ones
  assert.equal(perTurnEstimate([user(30), asst(70), user(0), asst(0), user(30), asst(50), user(30), asst(900)]), 80, "the median of 100, 0 and 80");
});

test("a turn holding a row the observer has not reported is dropped, never counted short", () => {
  const rows = [user(30), asst(70), user(30), asst(undefined), user(30), asst(50), user(30), asst(900)];
  assert.deepEqual(completeTurnHeights(rows), [100, 80], "the second turn is out: its reply has no height yet");
  assert.equal(perTurnEstimate(rows), 80);
  const noUserH = [row("turn turn-user", undefined), asst(70), user(30), asst(50), user(30), asst(40), user(30)];   // (user(undefined) would take the default height)
  assert.deepEqual(completeTurnHeights(noUserH), [80, 70], "an unreported user row voids its own turn");
});

test("spacers, gap elements and day dividers are not turn content: they neither start, end nor add to a turn", () => {
  const spacer = row("tx-spacer tx-spacer-top", 24000), gapEl = row("tx-gap", 3000), divider = row("day-divider", 24);
  assert.ok(isSpacerRow(spacer) && isSpacerRow(gapEl) && !isSpacerRow(divider));
  assert.ok(!isTurnRow(spacer) && !isTurnRow(gapEl) && !isTurnRow(divider));
  const rows = [spacer, gapEl, user(30), divider, asst(70), user(30), asst(90), divider, user(30), asst(900)];
  assert.deepEqual(completeTurnHeights(rows), [100, 120]);
  assert.equal(perTurnEstimate(rows), 100);
});

test("a gap element inside the window ends the open turn and starts none: the rows after it are no turn until the next visible user row (the maintainer's round 1 addendum, extra8-4)", () => {
  // two complete turns (100, 120), then a gap: the rows after it belong to a turn whose prompt lies inside the gap (a run opening with no
  // visible user row: a stripped record, an unplaced prefix). Under the old walk they joined the 120 px turn, which closed at the third
  // user row as 1120, so a partial turn inflated a measured one; the gap breaks the turn instead, and the streaming turn after it is
  // never counted, so the complete turns are the one closed before the gap
  const rows = [user(30), asst(70), user(30), asst(90), row("tx-gap", 3000), asst(1000), user(30), asst(50)];
  assert.deepEqual(completeTurnHeights(rows), [100], "the turn open at the gap (120) is dropped with the rows after it, never pushed as 1120");
  assert.equal(perTurnEstimate(rows), null, "one complete turn: no figure (the old walk read 100 off [100, 1120])");
  // a gap between two closed turns changes nothing: the turn before it closed at its own user row, and the next user row opens the next
  const closed = [user(30), asst(70), user(30), asst(90), user(30), row("tx-gap", 3000), user(30), asst(50), user(30)];
  assert.deepEqual(completeTurnHeights(closed), [100, 120, 80], "the gap drops the turn it interrupts (the 30 px prompt alone before it) and nothing else");
  // a plain spacer is not a gap: it neither breaks nor starts a turn (the top spacer precedes every window)
  assert.deepEqual(completeTurnHeights([row("tx-spacer tx-spacer-top", 5000), user(30), asst(70), user(30), asst(90), user(30)]), [100, 120]);
});

test("the median: the middle value, or at an even count the LOWER of the two middle values, so the figure is always a height some turn has", () => {
  assert.equal(median([]), null);
  assert.equal(median([7]), 7);
  assert.equal(median([100, 5000, 120]), 120, "one tall turn does not pull the figure the way a mean would");
  assert.equal(median([120, 100, 200, 110]), 110, "four values: the lower middle (their mean of two, 115, is a height none of them has)");
  assert.equal(median([3, 1, 2, 1000, 4]), 3);
  // the shape the maintainer's round 1 ruling found: three visible user rows around one long agentic turn give two complete turns, a short one and a long
  // one, and the mean of the two (6,905 px) drew a 200-turn head gap at the cap (480,000 px) as a figure no turn in the window had; the
  // lower middle is the short turn, and at four turns the same holds (the averaging closed at two would have returned at four)
  const two = [user(30), asst(70), user(30), asst(13680), user(30)];
  assert.deepEqual(completeTurnHeights(two), [100, 13710]);
  assert.equal(perTurnEstimate(two), 100, "a height a turn in the window has, never 6,905");
  assert.ok(completeTurnHeights(two).includes(perTurnEstimate(two)!), "the figure is one of the turns");
  const four = [user(30), asst(70), user(30), asst(70), user(30), asst(1000), user(30), asst(3000), user(30)];
  assert.deepEqual(completeTurnHeights(four), [100, 100, 1030, 3030]);
  assert.equal(median([100, 100, 1030, 3030]), 100, "the lower middle at four");
  assert.equal(perTurnEstimate(four), 100);
  assert.ok(completeTurnHeights(four).includes(perTurnEstimate(four)!), "…and one of the turns");
  assert.equal(MIN_COMPLETE_TURNS, 2, "two complete turns still suffice: the figure is an observed height at every count");
});

test("the rows' mean is over every non-spacer, non-gap child, a hidden row at 0 and a divider with its height, skipping unreported rows", () => {
  assert.equal(meanRowHeight([]), null);
  assert.equal(meanRowHeight([row("tx-spacer tx-spacer-top", 5000), row("tx-gap", 3000)]), null, "spacers and gaps feed nothing");
  assert.equal(meanRowHeight([user(30), asst(70)]), 50);
  assert.equal(meanRowHeight([user(30), row("day-divider", 20), asst(70)]), 40, "the divider counts, as the old measure counted every child");
  assert.equal(meanRowHeight([user(30), row("turn turn-user turn-echo-hidden", undefined, true), asst(90)]), 40, "a hidden row is a 0 in the population");
  assert.equal(meanRowHeight([user(30), asst(undefined), asst(90)]), 60, "an unreported row is not in the population");
  assert.equal(meanRowHeight([row("turn turn-user turn-echo-hidden", undefined, true)]), null, "a population of zeros is no measurement (never cache a 0)");
});

test("rowsFor reads the class list, the inline hidden state and the reported height through the caller's readers", () => {
  const heights = new Map<object, number>();
  const a = { className: "turn turn-user", style: { display: "" } }, b = { className: "turn turn-assistant", style: { display: "none" } }, c = { className: "day-divider", style: { display: "" } };
  heights.set(a, 33); heights.set(c, 20);
  const rows = rowsFor([a, b, c], (n) => n.className, (n) => n.style.display === "none", (n) => heights.get(n));
  assert.deepEqual(rows, [{ cls: "turn turn-user", hidden: false, h: 33 }, { cls: "turn turn-assistant", hidden: true, h: undefined }, { cls: "day-divider", hidden: false, h: 20 }]);
});

test("the gap's per-turn figure is capped at MAX_TURN_PX under every reader: a backstop, twenty default turns, not the estimate", () => {
  assert.equal(MAX_TURN_PX, 20 * DEFAULT_TURN_PX);
  assert.equal(gapHeight({ lo: 0, hi: 200 }, 7150), 200 * MAX_TURN_PX, "the old estimator's figure would have drawn 1.43M px; the cap holds it at 480k");
  assert.equal(gapHeight({ lo: 0, hi: 200 }, MAX_TURN_PX + 1), 200 * MAX_TURN_PX);
  assert.equal(gapHeight({ lo: 0, hi: 200 }, 110), 22000, "under the cap the figure is the figure");
  assert.equal(gapHeight({ lo: 0, hi: 200 }, null), 200 * DEFAULT_TURN_PX);
});
