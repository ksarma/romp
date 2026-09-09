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
  assert.match(SRC, /const differing = skipFlipOnce \? \[\] : FLY_COLS\.filter\(\(k\) => !sameKeySeq\(childKeys\(cols\[k\]\), buckets\[k\]\.map\(\(e\) => entryKey\(e, cols\[k\]\)\)\)\);\n\s*skipFlipOnce = false;\n\s*const flipCols = differing\.length && \(stackForced \|\| gprefs\.stacked\) \? FLY_COLS : differing;\n\s*const flipFirst = captureCardRects\(cols, flipCols\);/);
  assert.match(SRC, /flyColumnChanges\(flipFirst, cols, flipCols\);/);
  // 2026-09-07 (upstream #1016): the release paint after a hidden stretch skips the pass once. On the
  // per-column gate that is an empty differing list, so no column's rects are read and nothing flies; the
  // flag is spent before flipCols is derived (the regex above pins the order), so the very next render
  // decides on the painted DOM again. The arm and release paths are pinned in feed-hidden-paint.test.ts.
  assert.match(SRC, /let skipFlipOnce = false;/);
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

test("a card repaints only when its object or a board-level input it reads changed (feed-card-gate.ts)", () => {
  // the paint key that gated here before serialised every card per render and carried two whole-board terms
  // (a 15 s clock, an epoch bumped by every status-set and settings change); none of it remains
  assert.doesNotMatch(SRC, /cardPaintKey|paintEpoch|noteStatusInputs|_paintKey|button\[disabled\]/);
  // the import also carries sameKeySeq: the fork's per-column FLIP gate (pinned above) reads it
  assert.match(SRC, /import \{ cardInputsKey, cardNeedsUpdate, sameKeySeq, type GateEnv \} from "\.\/feed-card-gate";/);
  // reconcileCol gates the ask branch: a new object OR a new key repaints; the key is stored after the paint
  assert.match(SRC, /function reconcileCol\(listEl: HTMLElement, entries: Entry\[\], globalDesired: Set<string>, gate: GateEnv\)/);
  assert.match(SRC, /const ik = cardInputsKey\(e\.ask, gate\);\n\s*if \(cardNeedsUpdate\(card as any, e\.ask, ik\)\) \{ updateAskCard\(card, e\.ask\); \(card as any\)\._ik = ik; \}/);
  assert.match(SRC, /function updateAskCard\(card: HTMLElement, it: AskItem\) \{\n\s*const a = card as any;\n\s*a\._it = it;/,
    "updateAskCard stashes the object the gate compares, first thing");
  // the env, built once per render from everything a card's paint reads outside its object: the status sets and
  // self host, the hover/pin, the bell, the prefs, the host-down mark, the session's repository, and the fork's
  // user-todo count (the ⚑ marker). The clock is NOT among them: the 15 s live pass moves the stamped ages in
  // place instead of repainting cards.
  assert.match(SRC, /const gate: GateEnv = \{\n\s*dot: dotFor, working: \(n\) => workingSet\.has\(n\), userTodos: userTodosMap,\n\s*focusId: hoverAskId \?\? pinnedAskId, pinnedId: pinnedAskId, notifyOn: cardNotifyOn,\n\s*prefs: \{ grouped: gprefs\.grouped, collapsed: gprefs\.collapsed, colormap: gprefs\.colormap \},\n\s*hostDown: hostIsDown, selfHost: feedSelfHost, repo: prRepoOf, seq: \+\+renderSeq,\n\s*\};/);
  assert.match(SRC, /reconcileCol\(cols\.asks, buckets\.asks, desired, gate\);\n\s*reconcileCol\(cols\.needsInput, buckets\.needsInput, desired, gate\);\n\s*reconcileCol\(cols\.completed, buckets\.completed, desired, gate\);/);
  // the latches: the card's Retry is a manual retry, and each latch re-arms on the kernel's reply for ITS request
  // (review find, 2026-09-08): a refused apiRetry names the session, reviveFailed names the revived id
  assert.match(SRC, /vscodeApi\?\.postMessage\(\{ type: "apiRetry", id: it\.sid, manual: true \}\);/);
  assert.match(SRC, /showErrDialog\(title, m\.text, copy\);[\s\S]*?if \(op === "apiRetry" && sid\) rearmLatches\(\{ kind: "retry", sid \}\);/);
  assert.match(SRC, /m\.type === "reviveFailed" && typeof m\.id === "string" && m\.id\) \{[\s\S]*?rearmLatches\(\{ kind: "revive", id: m\.id \}\)/);
  assert.match(SRC, /\(a\._revive as any\)\._idle = a\._revive\.textContent;/);
  // Undo takes .dismissing off a card restored inside its collapse window (the class rewrite no longer does)
  assert.match(SRC, /askEls\.get\(it\.itemId\)\?\.classList\.remove\("dismissing"\);/);
  // executed: the same object under the same key is skipped; a re-sent object or a moved input repaints
  const it = { itemId: "a:1" };
  const card = { _it: it, _ik: "k" };
  assert.equal(cardNeedsUpdate(card, it, "k"), false);
  assert.equal(cardNeedsUpdate(card, { ...it }, "k"), true, "a new object is the kernel re-sending the card");
  assert.equal(cardNeedsUpdate(card, it, "k2"), true, "a board-level input moved");
});
