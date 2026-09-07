import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { flipNeeded } from "./feed-flip";
import { cardNeedsUpdate } from "./feed-card-gate";

const M = (o: Record<string, string>) => new Map(Object.entries(o));

test("no FLIP when every card kept its column (the everyday in-place update)", () => {
  assert.equal(flipNeeded(M({ "a:1": "asks", "a:2": "completed" }), M({ "a:1": "asks", "a:2": "completed" })), false);
});
test("a card that changed column needs the pass", () => {
  assert.equal(flipNeeded(M({ "a:1": "asks", "a:2": "asks" }), M({ "a:1": "asks", "a:2": "needsInput" })), true);
});
test("a card that moved within its column needs the pass too (the user 2026-06-29: in-column shifters glide)", () => {
  assert.equal(flipNeeded(M({ "a:1": "asks:0", "a:2": "asks:1" }), M({ "a:1": "asks:1", "a:2": "asks:0" })), true);
  assert.equal(flipNeeded(M({ "a:1": "asks:0", "a:2": "asks:1" }), M({ "a:1": "asks:0", "a:2": "asks:1" })), false);
});
test("a card that appeared or left needs the pass (its neighbours shift)", () => {
  assert.equal(flipNeeded(M({ "a:1": "asks" }), M({ "a:1": "asks", "a:2": "asks" })), true);
  assert.equal(flipNeeded(M({ "a:1": "asks", "a:2": "asks" }), M({ "a:1": "asks" })), true);
  assert.equal(flipNeeded(M({ "a:1": "asks" }), M({ "a:9": "asks" })), true, "same count, different card");
});
test("the first paint never flies", () => {
  assert.equal(flipNeeded(new Map(), M({ "a:1": "asks" })), false);
});

const SRC = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "feed.ts"), "utf8");
// The 2026-09-07 upstream fold kept the fork's PER-COLUMN gate over this module's board-level one (uirender
// DECISION 2): feed.ts never imports flipNeeded. flipNeeded stays a pure module with the unit tests above;
// the pins below name the shipped shape (vscode-extension/src/feed-fly.test.ts carries the fuller set).
test("render() gates both forced layouts on the flip decision, and remembers the columns it painted", () => {
  // the decision is per column, read off the DOM itself: a column whose current key sequence equals the
  // planned one moved nothing, so neither its rects nor its fly are read or written; the stacked layout
  // (where a change in one section shifts the sections below it) widens a hit to every column
  assert.match(SRC, /const differing = FLY_COLS\.filter\(\(k\) => !sameKeySeq\(childKeys\(cols\[k\]\), buckets\[k\]\.map\(\(e\) => entryKey\(e, cols\[k\]\)\)\)\);\n\s*const flipCols = differing\.length && \(stackForced \|\| gprefs\.stacked\) \? FLY_COLS : differing;\n\s*const flipFirst = captureCardRects\(cols, flipCols\);/);
  assert.match(SRC, /flyColumnChanges\(flipFirst, cols, flipCols\);/);
  // what it remembers is the painted DOM: the keys reconcileCol wrote are what the next render compares the
  // plan against (childKeys/entryKey), so no prevCols/columnsOf ledger exists beside them
  assert.match(SRC, /import \{ cardInputsKey, cardNeedsUpdate, sameKeySeq, type GateEnv \} from "\.\/feed-card-gate";/);
  assert.match(SRC, /function entryKey\(e: Entry, listEl: HTMLElement\): string \{/);
  assert.match(SRC, /function childKeys\(listEl: HTMLElement\): string\[\] \{/);
  assert.ok(!/flipNeeded|columnsOf\(|prevCols/.test(SRC), "the board-level gate is not the shipped one");
});
test("the fly reads every rect before it writes any transform", () => {
  const body = /function flyColumnChanges\([\s\S]*?\n\}/.exec(SRC)![0];
  const firstWrite = body.indexOf("c.style.transform = ");
  const lastRead = body.lastIndexOf("getBoundingClientRect()");
  assert.ok(firstWrite > 0 && lastRead > 0 && lastRead < firstWrite, "all reads precede the first write");
  assert.match(body, /const moves: \{ c: HTMLElement; dx: number; dy: number; crossed: boolean \}\[\] = \[\];/);
});

test("a card whose data and display state did not change is not repainted", () => {
  // the fold kept the fork's gate (feed-card-gate.ts, at the reconcile call site) over this module's
  // cardPaintKey/paintEpoch (uirender flags, 2026-09-07): a kept card repaints only when the kernel re-sent it
  // (a new object; the delta path keeps an unchanged card's object by reference) or a board-level input it
  // reads changed (the key). Placement stays unconditional, so a column or sort change still moves it.
  // feed-render-incremental.test.ts drives the contract (frames C and D, the Retry latch); this pins the seam.
  assert.match(SRC, /const ik = cardInputsKey\(e\.ask, gate\);\n\s*if \(cardNeedsUpdate\(card as any, e\.ask, ik\)\) \{ updateAskCard\(card, e\.ask\); \(card as any\)\._ik = ik; \}/);
  // the inputs every card reads that live outside its item, resolved once per render: the status sets and
  // self host, the hover/pin, the bell, the prefs, the host-down mark, the user-todo count. The clock is
  // NOT among them: the 15 s live pass moves the stamped ages in place instead of repainting cards.
  assert.match(SRC, /const gate: GateEnv = \{\n\s*dot: dotFor, working: \(n\) => workingSet\.has\(n\), userTodos: userTodosMap,\n\s*focusId: hoverAskId \?\? pinnedAskId, pinnedId: pinnedAskId, notifyOn: cardNotifyOn,\n\s*prefs: \{ grouped: gprefs\.grouped, collapsed: gprefs\.collapsed, colormap: gprefs\.colormap \},\n\s*hostDown: hostIsDown, selfHost: feedSelfHost, seq: \+\+renderSeq,/);
  // executed: the same object under the same key is skipped; a re-sent object or a moved input repaints
  const it = { itemId: "a:1" };
  const card = { _it: it, _ik: "k" };
  assert.equal(cardNeedsUpdate(card, it, "k"), false);
  assert.equal(cardNeedsUpdate(card, { ...it }, "k"), true, "a new object is the kernel re-sending the card");
  assert.equal(cardNeedsUpdate(card, it, "k2"), true, "a board-level input moved");
  assert.ok(!/cardPaintKey|paintEpoch|noteStatusInputs/.test(SRC), "the JSON-plus-clock gate is not the shipped one");
});
