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
  assert.equal(perTurnEstimate(rows), 110);
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
  assert.equal(perTurnEstimate([user(30), asst(70), user(30), asst(50), user(30)]), 90, "two complete turns (100 and 80): their mean, the median of two");
});

test("the figure is whole pixels: sub-pixel layout differences between two windows of the same turns are not a change", () => {
  // rows lay out at fractions of a pixel (a 27.09375 px row was read in the landing lab); over a 200-turn gap a thirty-second of a pixel
  // per turn is 7 px of spacer movement to compensate for nothing
  const a = [user(30.03125), asst(70.0625), user(30), asst(90.03125), user(30), asst(900)];
  const b = [user(30), asst(70), user(30.09375), asst(90), user(30), asst(900)];
  assert.equal(perTurnEstimate(a), 110); assert.equal(perTurnEstimate(b), 110);
  assert.equal(median([100.09375, 120.03125]), 110.0625, "the median itself keeps the fraction; the figure rounds it");
  assert.equal(perTurnEstimate([user(30), asst(70.6), user(30), asst(70.6), user(30)]), 101, "…to the nearest pixel");
});

test("the trailing turn is the one streaming and is never counted, so a growing reply moves no figure", () => {
  const rows = [user(30), asst(70), user(30), asst(90), user(30), asst(100)];
  const before = perTurnEstimate(rows);
  rows[5] = asst(5000);
  assert.equal(perTurnEstimate(rows), before, "the last turn grew by 4,900 px and the figure stood");
  assert.equal(before, 110);
});

test("a hidden user row (a stripped record, the echo of a send) starts no turn: a long turn holding one stays one turn", () => {
  const stripped = row("turn turn-user turn-user-empty", undefined, true), echo = row("turn turn-user turn-echo-hidden", 0, true);
  assert.ok(!isUserRow(stripped) && !isUserRow(echo) && isTurnRow(stripped), "hidden user rows are turn rows that start nothing");
  const rows = [user(30), asst(100), stripped, tool(50), echo, asst(100), user(30), asst(40), user(30), asst(900)];
  assert.deepEqual(completeTurnHeights(rows), [280, 70], "one turn of 280 px, not two turns split at the hidden rows");
  assert.equal(perTurnEstimate(rows), 175);
});

test("a turn holding a row the observer has not reported is dropped, never counted short", () => {
  const rows = [user(30), asst(70), user(30), asst(undefined), user(30), asst(50), user(30), asst(900)];
  assert.deepEqual(completeTurnHeights(rows), [100, 80], "the second turn is out: its reply has no height yet");
  assert.equal(perTurnEstimate(rows), 90);
  const noUserH = [row("turn turn-user", undefined), asst(70), user(30), asst(50), user(30), asst(40), user(30)];   // (user(undefined) would take the default height)
  assert.deepEqual(completeTurnHeights(noUserH), [80, 70], "an unreported user row voids its own turn");
});

test("spacers, gap elements and day dividers are not turn content: they neither start, end nor add to a turn", () => {
  const spacer = row("tx-spacer tx-spacer-top", 24000), gapEl = row("tx-gap", 3000), divider = row("day-divider", 24);
  assert.ok(isSpacerRow(spacer) && isSpacerRow(gapEl) && !isSpacerRow(divider));
  assert.ok(!isTurnRow(spacer) && !isTurnRow(gapEl) && !isTurnRow(divider));
  const rows = [spacer, gapEl, user(30), divider, asst(70), user(30), asst(90), divider, user(30), asst(900)];
  assert.deepEqual(completeTurnHeights(rows), [100, 120]);
  assert.equal(perTurnEstimate(rows), 110);
});

test("the median: the middle value, or the mean of the two middle values", () => {
  assert.equal(median([]), null);
  assert.equal(median([7]), 7);
  assert.equal(median([100, 5000, 120]), 120, "one tall turn does not pull the figure the way a mean would");
  assert.equal(median([120, 100, 200, 110]), 115);
  assert.equal(median([3, 1, 2, 1000, 4]), 3);
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
