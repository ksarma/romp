// The feed applies every payload while the tab is hidden but paints none of them (the user 2026-09-07,
// whose dashboard froze on the return to its browser tab): each hidden render was a full paint — the FLIP
// pass's two forced layouts and a double rAF per moved card all piled onto the return frame. Now render()
// is owed while nobody can see the pane and settled ONCE, synchronously, on the event that shows it, with
// the flip skipped (cards that moved while away snap into place: motion without new information, the
// 2026-07-29 rule). State keeps flowing: the follow-move backstop must find its prediction already
// confirmed by a payload applied hidden, or it would revert a move the kernel had confirmed.
//
// feed.ts has import-time DOM side effects (the repo convention: no test imports it), so this has two
// halves — the harness below runs the PINNED lines against the pure modules they call (paint-gate.ts,
// feed-card-gate.ts), and the source pins hold feed.ts to exactly that wiring.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { paintHeld, paintReleased } from "./paint-gate";
import { sameKeySeq } from "./feed-card-gate";

type Ask = { itemId: string; column: string };
type Payload = { asks: Ask[] };
const COLS = ["asks", "needsInput", "completed"] as const;   // feed.ts FLY_COLS

// The harness: feed.ts's render() gate, flip decision, release path and the follow-move backstop, line for
// line (the pins below are what keep this honest), over a list whose "content" is its painted cards. The
// fork's flip decision is PER COLUMN (feed-card-gate.ts sameKeySeq: a column's DOM key sequence against its
// planned one; a prior fold ruled it over upstream's board-level flipNeeded/prevCols, and this fold kept it,
// ui-code DECISION 2), so the painted key sequences stand in for the columns' DOM here.
function feedHarness() {
  const st = {
    hidden: false, intersecting: true,
    asks: [] as Ask[], painted: 0,                     // painted = list.childElementCount after the last paint
    pendingFollowMove: new Map<string, true>(),
    paintDirty: false, skipFlipOnce: false,
    domKeys: { asks: [], needsInput: [], completed: [] } as Record<string, string[]>,   // childKeys(cols[k]) after the last paint
    paints: 0, flipChecks: 0, lastFlipCols: null as string[] | null,
  };
  // the planned key sequence per column (bucketed like reconcileCol's input; a working card sits in the asks column)
  const planned = (asks: Ask[]) => {
    const b: Record<string, string[]> = { asks: [], needsInput: [], completed: [] };
    for (const a of asks) b[(COLS as readonly string[]).includes(a.column) ? a.column : "asks"].push("a:" + a.itemId);
    return b;
  };
  const sameKeySeqSpy = (a: readonly string[], b: readonly string[]) => { st.flipChecks++; return sameKeySeq(a, b); };
  function render() {
    if (paintHeld(st.hidden, st.intersecting, st.painted > 0)) { st.paintDirty = true; return; }
    const buckets = planned(st.asks);
    const differing = st.skipFlipOnce ? [] : COLS.filter((k) => !sameKeySeqSpy(st.domKeys[k], buckets[k]));
    st.skipFlipOnce = false;
    st.lastFlipCols = differing;
    for (const k of COLS) st.domKeys[k] = buckets[k];   // reconcileCol writes the planned sequence into each column
    st.paints++; st.painted = st.asks.length;
  }
  // applyFeedPayload: model swap + reconcileFollowMove (a prediction the kernel now lists as working is
  // confirmed → dropped) + render(); nothing here looks at the visibility
  function applyFeedPayload(m: Payload) {
    st.asks = m.asks;
    for (const id of Array.from(st.pendingFollowMove.keys())) {
      const a = m.asks.find((x) => x.itemId === id);
      if (!a || a.column === "working") st.pendingFollowMove.delete(id);
    }
    render();
  }
  // ackFollowMove's backstop timer body
  function backstop(itemId: string): "kept" | "reverted" {
    if (!st.pendingFollowMove.has(itemId)) return "kept";
    st.pendingFollowMove.delete(itemId); render(); return "reverted";
  }
  function releasePaint() {
    if (!paintReleased(st.paintDirty, st.hidden, st.intersecting)) return;
    st.paintDirty = false;
    st.skipFlipOnce = true;
    render();
  }
  return { st, render, applyFeedPayload, backstop, releasePaint, planned };
}

test("hidden → ten payloads → zero paints, while the asks model and the follow-move bookkeeping keep updating", () => {
  const f = feedHarness();
  f.applyFeedPayload({ asks: [{ itemId: "g1", column: "asks" }, { itemId: "g2", column: "needsInput" }] });   // first content, visible
  assert.equal(f.st.paints, 1);
  f.st.pendingFollowMove.set("g2", true);          // the user replied to g2: predicted into Working
  f.st.hidden = true;                              // the tab goes to the background
  for (let i = 0; i < 10; i++) {
    f.applyFeedPayload({ asks: [{ itemId: "g1", column: "asks" }, { itemId: "g2", column: i >= 3 ? "working" : "needsInput" }, { itemId: "g" + (10 + i), column: "asks" }] });
  }
  assert.equal(f.st.paints, 1, "no paint while hidden");
  assert.equal(f.st.paintDirty, true, "a paint is owed");
  assert.equal(f.st.asks.length, 3, "the model is the newest payload's");
  assert.equal(f.st.asks[2].itemId, "g19");
  assert.equal(f.st.pendingFollowMove.size, 0, "the confirming payload (g2 working) retired the prediction while hidden");
});

test("the follow-move backstop that fires after a confirming payload was applied hidden does not revert", () => {
  const f = feedHarness();
  f.applyFeedPayload({ asks: [{ itemId: "g2", column: "needsInput" }] });
  f.st.pendingFollowMove.set("g2", true);
  f.st.hidden = true;
  f.applyFeedPayload({ asks: [{ itemId: "g2", column: "working" }] });   // the kernel confirms while the tab is hidden
  assert.equal(f.backstop("g2"), "kept", "MOVE_ACK_MS elapses: the prediction is already confirmed, nothing to revert");
  assert.equal(f.st.paints, 1, "and the backstop's render() is held like any other");
});

test("release → exactly one synchronous paint, no column flies, and the painted key sequences are the next flip baseline", () => {
  const f = feedHarness();
  f.applyFeedPayload({ asks: [{ itemId: "g1", column: "asks" }, { itemId: "g2", column: "needsInput" }] });
  f.st.hidden = true;
  f.applyFeedPayload({ asks: [{ itemId: "g2", column: "completed" }, { itemId: "g1", column: "working" }] });   // both moved while away
  f.applyFeedPayload({ asks: [{ itemId: "g2", column: "completed" }, { itemId: "g1", column: "working" }, { itemId: "g3", column: "asks" }] });
  const checksBefore = f.st.flipChecks;
  f.st.hidden = false; f.releasePaint();           // visibilitychange → visible
  assert.equal(f.st.paints, 2, "one paint for the whole hidden stretch");
  assert.deepEqual(f.st.lastFlipCols, [], "cards snap into place: no column differs for the release paint");
  assert.equal(f.st.flipChecks, checksBefore, "sameKeySeq was not even consulted");
  assert.deepEqual(f.st.domKeys, f.planned(f.st.asks), "the columns' key sequences, the next flip baseline, are what was painted");
  assert.equal(f.st.paintDirty, false);
  f.releasePaint();                                // a second release event (the observer's callback) owes nothing
  assert.equal(f.st.paints, 2);
  // the NEXT move, seen live, glides again: the skip was one-shot
  f.applyFeedPayload({ asks: [{ itemId: "g1", column: "working" }, { itemId: "g2", column: "completed" }, { itemId: "g3", column: "completed" }] });
  assert.equal(f.st.paints, 3);
  assert.deepEqual(f.st.lastFlipCols, ["asks", "completed"], "g3 left asks for completed: both columns fly");
});

test("a display:none pane holds too, and the tab's return alone does not release it — the observer does", () => {
  const f = feedHarness();
  f.applyFeedPayload({ asks: [{ itemId: "g1", column: "asks" }] });
  f.st.intersecting = false; f.st.hidden = true;
  f.applyFeedPayload({ asks: [{ itemId: "g1", column: "working" }] });
  f.st.hidden = false; f.releasePaint();
  assert.equal(f.st.paints, 1, "tab back, pane still display:none");
  f.st.intersecting = true; f.releasePaint();
  assert.equal(f.st.paints, 2);
});

// ── source pins: feed.ts wires exactly the lines the harness ran ──
const SRC = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "feed.ts"), "utf8");
const body = (name: string) => new RegExp("^function " + name + "\\([\\s\\S]*?\\n\\}", "m").exec(SRC)![0];

test("render() is gated first, on the shared pure decision, and nothing else in feed.ts is", () => {
  assert.match(SRC, /import \{ paintHeld, paintReleased \} from "\.\/paint-gate";/);
  assert.match(SRC, /function render\(\) \{\n  const list = document\.getElementById\("feed-list"\)!;\n  if \(!feedWatching\) \{ feedWatching = true; watchFeedVisibility\(list\); \}\n  if \(paintHeld\(document\.hidden, feedIntersecting, list\.childElementCount > 0\)\) \{ paintDirty = true; return; \}\n  pruneTip\(\);/,
    "the gate precedes every paint-side step (pruneTip, applyFollowMove, the footer, the columns)");
  // two gates, both PAINTS: render(), and the 15 s age pass (feed-age.ts liveRefresher) that rewrites the stamped
  // labels on the cards render() did not repaint — it reads the same decision, so the feed has one meaning of
  // "hidden"; no state path is withheld
  assert.equal(SRC.split("paintHeld(").length - 1, 2, "two gates: render() and the age pass; no other path is withheld");
  assert.match(SRC, /const live = liveRefresher\(\{ hidden: \(\) => paintHeld\(document\.hidden, feedIntersecting, true\), pass: livePass \}\);/);
  // the fork's line (2026-09-08 fold, round 3): the observer's word starts null so the shim's word is not published
  // before it speaks (federation-hidden-hold.test.ts); the gate reads null as upstream's `let feedIntersecting = true;`
  assert.match(SRC, /let feedIntersecting: boolean \| null = null;/, "on screen until the observer says otherwise: no observer → the tab alone gates");
});

test("the flip is skipped exactly once after a release, and the painted key sequences are still the next baseline", () => {
  // the fork's per-column gate (feed-card-gate.ts sameKeySeq) in place of upstream's flipNeeded/prevCols, ui-code
  // DECISION 2: the snap empties the differing set and is spent before flipCols; reconcileCol then writes the
  // painted sequences, which the next render compares against
  assert.match(SRC, /const differing = skipFlipOnce \? \[\] : FLY_COLS\.filter\(\(k\) => !sameKeySeq\(childKeys\(cols\[k\]\), [\s\S]*?\);\n\s*skipFlipOnce = false;\n\s*const flipCols = /);
  assert.doesNotMatch(SRC, /flipNeeded|columnsOf\(|prevCols/, "no board-level flip baseline beside the per-column gate");
  assert.match(SRC, /askEls\.clear\(\); groupEls\.clear\(\);\n\s*skipFlipOnce = false;/, "the empty-board paint spends the snap too");
  const rel = body("releasePaint");
  assert.match(rel, /if \(!paintReleased\(paintDirty, document\.hidden, feedIntersecting\)\) return;\n\s*paintDirty = false;\n\s*skipFlipOnce = true;\n\s*render\(\);/);
  assert.doesNotMatch(rel, /requestAnimationFrame|setTimeout|queueMicrotask/, "the release paints synchronously: the earliest fresh frame after the compositor's cached one");
});

test("BOTH release events run the same release: visibilitychange→visible and the observer's callback", () => {
  assert.match(SRC, /document\.addEventListener\("visibilitychange", \(\) => \{ if \(!document\.hidden\) releasePaint\(\); \}\);/);
  const watch = body("watchFeedVisibility");
  assert.match(watch, /new IntersectionObserver\(\(entries\) => \{\n\s*feedIntersecting = entries\.some\(\(e\) => e\.isIntersecting\);\n\s*releasePaint\(\);\n\s*live\.catchUp\(\);[^\n]*\n\s*\}\)\.observe\(list\);/);
  assert.match(watch, /if \(typeof IntersectionObserver === "undefined"\) return;/);
});

test("state is applied whatever the visibility: the payload path and its bookkeeping never look at the gate", () => {
  const apply = body("applyFeedPayload");
  assert.doesNotMatch(apply, /document\.hidden|paintDirty|feedIntersecting|paintHeld/);
  for (const must of ["reconcileFollowMove(", "mirrorBadges(", "clearUndoBusy();", "pendingCleared", "pendingRestored", "reconcilePendingDone("]) {
    assert.ok(apply.includes(must), "applyFeedPayload still runs " + must);
  }
  assert.equal((apply.match(/\brender\(\);/g) || []).length, 1, "ONE gated render");
  assert.match(apply, /\n  render\(\);\n  if \(!feedAnnounced\) \{/, "…followed only by the shell's first-content announcement");
  // the message handler applies live unless a card is hovered/keyed — the hover-freeze holder is not
  // widened into a hidden holder (it withholds the payload itself, which the backstop test above forbids)
  assert.match(SRC, /if \(m\.type === "feed"\) \{[\s\S]*?if \(freezeKey \|\| tabScopeKey\) \{ pendingFeedPayload = m; paintFreezeBadges\(\); return; \}\n\s*applyFeedPayload\(m\);/);
  assert.doesNotMatch(SRC, /freezeKey \|\| tabScopeKey \|\| document\.hidden|document\.hidden \|\| freezeKey/);
});

test("the follow-move backstop yields to a prediction a payload already retired; the payload retires it on `working`", () => {
  const ack = body("ackFollowMove");
  const guard = ack.indexOf('if (!pendingFollowMove.has(itemId)) return;\n    clearFollowMove(itemId, "backstop-noconfirm"); render();');
  assert.ok(guard > 0, "the backstop checks the prediction still stands before it reverts");
  assert.match(body("reconcileFollowMove"), /if \(!a \|\| a\.column === "working" \|\| pendingMoveKind\.get\(id\) === "answer"\) \{\n\s*clearFollowMove\(/);
});

test("a bell jump settles the owed paint on the shell's word before it looks for the card", () => {
  // the shell shows the pane and posts revealCard in the same task, before the observer re-measures
  assert.match(SRC, /if \(m\.romp === "revealCard"\) \{[\s\S]*?if \(paintDirty\) \{ feedIntersecting = true; releasePaint\(\); \}\n\s*const key = "a:" \+ String\(m\.itemId \|\| ""\);/);
});
