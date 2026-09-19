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
// feed-card-gate.ts), and the source pins hold feed.ts to exactly that wiring. The visibility wiring itself (the
// pane's hidden word for the kernel's pane shim) is lifted from feed.ts and run at the end.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { paintHeld, paintReleased, publishPaneHidden, firstPaintHeld, viewportHiddenSinceLoad, revealDecision, type PaneHiddenHost } from "./paint-gate";
import { sameKeySeq } from "./feed-card-gate";
import { searchMatches, searchSids } from "./feed-search";   // the real modules feed.ts's lifted paint plan calls (review round 2)
import { lensAll, lensUnions, lensVisible } from "./tag-lens";
import { hideEdges } from "../test-dom-shim";   // the fake-DOM rule (ui/test-dom-shim.test.ts): a window stand-in with a parent edge enumerates its primitives alone

const requireCjs = createRequire(__filename);

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
  assert.match(SRC, /import \{ paintHeld, paintReleased, publishPaneHidden \} from "\.\/paint-gate";\nimport \{ firstPaintHeld, viewportHiddenSinceLoad, revealDecision \} from "\.\/paint-gate";/, "the merged import is upstream's line (federation-hidden-hold.test.ts pins it); the first-paint hold's import, with the reveal's decision, is the fork's own line");
  assert.match(SRC, /function render\(\) \{\n  const list = document\.getElementById\("feed-list"\)!;\n  if \(!feedWatching\) \{ feedWatching = true; watchFeedVisibility\(list\); \}\n  if \(paintHeld\(document\.hidden, seenNow\(\), list\.childElementCount > 0\) \|\| firstPaintHeld\(list\.childElementCount > 0, parentMobile\(\), feedShellOn, viewportHiddenSinceLoad\(window\), seenNow\(\)\)\) \{ paintDirty = true; if \(list\.childElementCount === 0\) firstPaintHoldTold\(\); return; \}\n  pruneTip\(\);/,
    "the gate precedes every paint-side step (pruneTip, applyFollowMove, the footer, the columns); the phone's first-paint hold rides the same line (stage 0, 2026-09-18); the paint's measure is seenNow(), the observer's word or the show override (review round 2, D4), and a held FIRST paint tells the pane loader once (D3)");
  assert.match(SRC, /^let revealShown = false;\nfunction seenNow\(\): boolean \| null \{ return revealShown \? true : feedIntersecting; \}/m, "the show override is its own flag, read as the paint's measure alone; the observer's variable is the observer's");
  assert.equal((SRC.match(/feedIntersecting = /g) || []).length, 1, "ONE write to the observer's variable: its own callback (review round 2, D4: a reveal or a show word used to write it and nothing restored it)");
  // two gates, both PAINTS: render(), and the 15 s age pass (feed-age.ts liveRefresher) that rewrites the stamped
  // labels on the cards render() did not repaint — it reads the same decision, so the feed has one meaning of
  // "hidden"; no state path is withheld
  assert.equal(SRC.split("paintHeld(").length - 1, 2, "two gates: render() and the age pass; no other path is withheld");
  assert.match(SRC, /const live = liveRefresher\(\{ hidden: \(\) => paintHeld\(document\.hidden, feedIntersecting, true\), pass: livePass \}\);/);
  assert.match(SRC, /let feedIntersecting: boolean \| null = null;/, "the observer's word, null until it speaks: the gate reads null as on screen (no observer → the tab alone gates), and nothing is published for it");
  assert.equal(SRC.split("firstPaintHeld(").length - 1, 1, "one first-paint site: render()");
});

test("the flip is skipped exactly once after a release, and the painted key sequences are still the next baseline", () => {
  // the fork's per-column gate (feed-card-gate.ts sameKeySeq) in place of upstream's flipNeeded/prevCols, ui-code
  // DECISION 2: the snap empties the differing set and is spent before flipCols; reconcileCol then writes the
  // painted sequences, which the next render compares against
  assert.match(SRC, /const differing = skipFlipOnce \? \[\] : FLY_COLS\.filter\(\(k\) => !sameKeySeq\(childKeys\(cols\[k\]\), [\s\S]*?\);\n\s*skipFlipOnce = false;\n\s*const flipCols = /);
  assert.doesNotMatch(SRC, /flipNeeded|columnsOf\(|prevCols/, "no board-level flip baseline beside the per-column gate");
  assert.match(SRC, /askEls\.clear\(\); groupEls\.clear\(\);\n\s*skipFlipOnce = false;/, "the empty-board paint spends the snap too");
  const rel = body("releasePaint");
  assert.match(rel, /function releasePaint\(\): void \{\n\s*publishPaneHidden\(document\.hidden, feedIntersecting\);\n\s*if \(!paintReleased\(paintDirty, document\.hidden, seenNow\(\)\)\) return;\n\s*paintDirty = false;\n\s*skipFlipOnce = true;\n\s*render\(\);/,
    "the release publishes the pane's word for the kernel's pane shim first (paint-gate.ts publishPaneHidden, the observer's word alone: the override is never published, D4), then settles the owed paint on the paint's measure");
  assert.match(rel, /render\(\);\n\s*if \(firstHoldTold && !firstHoldReleased && !paintDirty\) \{ firstHoldReleased = true; try \{ window\.dispatchEvent\(new Event\("romp:firstpaintreleased"\)\); \} catch \{[^}]*\} \}/,
    "the pane loader's backstop resumes once, after the release render painted (a release that re-held dispatches nothing), D3");
  assert.doesNotMatch(rel, /requestAnimationFrame|setTimeout|queueMicrotask/, "the release paints synchronously: the earliest fresh frame after the compositor's cached one");
});

test("BOTH release events run the same release: visibilitychange→visible and the observer's callback", () => {
  assert.match(SRC, /document\.addEventListener\("visibilitychange", \(\) => \{ if \(!document\.hidden\) releasePaint\(\); \}\);/);
  assert.match(SRC, /document\.addEventListener\("visibilitychange", \(\) => \{ if \(document\.hidden\) publishPaneHidden\(true, feedIntersecting\); \}\);/,
    "the hidden arm releases nothing, so it publishes the pane's word itself");
  assert.equal(SRC.split("publishPaneHidden(").length - 1, 2, "two publish sites, both on the gate's events; no timer");
  const watch = body("watchFeedVisibility");
  assert.match(watch, /new IntersectionObserver\(\(entries\) => \{\n\s*const was = feedIntersecting;\n\s*feedIntersecting = entries\.some\(\(e\) => e\.isIntersecting\);\n\s*revealShown = false;[^\n]*\n\s*if \(was === true && !feedIntersecting\) pendingRevealKey = null;[^\n]*\n\s*releasePaint\(\);\n\s*live\.catchUp\(\);[^\n]*\n\s*\}\)\.observe\(list\);/,
    "the observer's callback: its word, the show override spent (D4), a hide after a show drops a parked jump (D5), then the release and the age pass");
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

test("a bell jump settles the owed paint on the shell's word before it looks for the card, through the show override, unless the shell's word says the pane is off screen", () => {
  // the shell shows the pane and posts revealCard in the same task, before the observer re-measures (review round 2, D4: the override
  // flag, never the observer's variable; and no release attempt for a pane the shell has off screen, the phone's bell row)
  assert.match(SRC, /if \(m\.romp === "revealCard"\) \{[\s\S]*?if \(paintDirty && feedShellOn !== false\) \{ revealShown = true; releasePaint\(\); \}\n\s*const key = "a:" \+ String\(m\.itemId \|\| ""\);/);
});

// ── the wiring, run: feed.ts's own visibility lines over the pure module ──
// The pins above hold the text; this lifts it. The slice from `let feedIntersecting` through render()'s gate (the
// line before `pruneTip();`) is feed.ts's text, transpiled with esbuild at run time and closed with a stand-in for
// the rest of the paint (the chat-exact-tail-exec.test.ts pattern). The page is stood in: `document` (hidden, the
// two visibilitychange listeners, the list by id), `IntersectionObserver` (its callback kept for the test to fire),
// `live` (the age pass's catch-up, counted) and the publisher bound to `host`, the window stand-in the pane's word
// lands on (feed.ts passes two arguments, so the page's window is the host). What the harness above cannot show:
// the word feed.ts publishes, on feed.ts's own events, and nothing before the observer has spoken.
type Cb = (entries: { isIntersecting: boolean }[]) => void;
function feedWiring(win: { parentProbe?: () => boolean; innerWidth?: number; innerHeight?: number } = {}) {
  const start = "let feedIntersecting: boolean | null = null;", end = "  pruneTip();";
  const a = SRC.indexOf(start), b = SRC.indexOf(end, a);
  assert.ok(a > 0 && b > a, "the wiring's anchors moved; re-anchor");
  const js = requireCjs("esbuild").transformSync(SRC.slice(a, b) + "  paint();\n}\n", { loader: "ts" }).code;
  const st = { hidden: false, model: 0, painted: 0, paints: 0, catchUps: 0, host: {} as PaneHiddenHost };
  const listeners: Array<() => void> = [];
  let observerCb: Cb | null = null;
  const list = { get childElementCount() { return st.painted; } };
  const fakeDocument = {
    get hidden() { return st.hidden; },
    addEventListener(_type: string, fn: () => void) { listeners.push(fn); },
    getElementById(id: string) { return id === "feed-list" ? list : null; },
  };
  class FakeObserver { constructor(cb: Cb) { observerCb = cb; } observe(_target: unknown) {} }
  const prelude = `
    const paintHeld = P.paintHeld, paintReleased = P.paintReleased, firstPaintHeld = P.firstPaintHeld, viewportHiddenSinceLoad = P.viewportHiddenSinceLoad;
    const publishPaneHidden = (docHidden, intersecting) => P.publishPaneHidden(docHidden, intersecting, S.host);
    const live = { catchUp() { S.catchUps++; } };
    const paint = () => { S.paints++; S.painted = S.model; };
  `;
  // the page's window stand-in: a phone shell publishes its layout probe on the parent (parentMobile reads it), a standalone
  // page is its own parent; the viewport is the shim's zero-viewport probe (a frame hidden since load reads 0)
  const events: string[] = [];
  const fakeWindow: any = { innerWidth: win.innerWidth ?? 800, innerHeight: win.innerHeight ?? 600, dispatchEvent(e: { type: string }) { events.push(e.type); return true; } };
  fakeWindow.parent = win.parentProbe ? { __rompMobileOn: win.parentProbe } : fakeWindow;
  hideEdges(fakeWindow);
  class FakeEvent { type: string; constructor(t: string) { this.type = t; } }
  const api = new Function("P", "S", "document", "IntersectionObserver", "window", "Event", prelude + js + "\nreturn { render, releasePaint };")(
    { paintHeld, paintReleased, publishPaneHidden, firstPaintHeld, viewportHiddenSinceLoad }, st, fakeDocument, FakeObserver, fakeWindow, FakeEvent) as { render(): void; releasePaint(): void };
  return {
    st, events,
    /** the shell's synchronous show hook, as feed.ts publishes it on the page's window (D3) */
    shown() { assert.equal(typeof fakeWindow.__rompPaneShown, "function", "feed.ts publishes window.__rompPaneShown"); fakeWindow.__rompPaneShown(); },
    /** the payload path's one gated render() */
    frame(n: number) { st.model = n; api.render(); },
    /** the IntersectionObserver's callback over #feed-list */
    observer(intersecting: boolean) { assert.ok(observerCb, "render() installed the observer"); observerCb!([{ isIntersecting: intersecting }]); },
    /** the tab's visibilitychange: feed.ts's two listeners run, the visible arm's release and the hidden arm's publish */
    tab(state: "hidden" | "visible") { st.hidden = state === "hidden"; for (const fn of listeners) fn(); },
    /** the iframe's viewport as the shim's probe reads it: 0 while display:none, its size once shown (every browser lays a shown frame out before the observer's callback runs) */
    viewport(w: number, h: number) { fakeWindow.innerWidth = w; fakeWindow.innerHeight = h; },
  };
}

test("run: feed.ts's own wiring publishes the pane's word on its events, nothing before the observer's first word, and the hidden arm publishes without a release", () => {
  const f = feedWiring();
  f.frame(1);                                          // the first payload: paints through and installs the observer
  assert.equal(f.st.paints, 1);
  assert.equal(typeof f.st.host.__rompPaneHidden, "undefined", "a frame is not a gate event, and the observer has not spoken: the shim's probe decides");
  f.tab("hidden"); f.tab("visible");
  assert.equal(typeof f.st.host.__rompPaneHidden, "undefined", "a visibilitychange on either arm before the observer's first entry publishes nothing");
  f.observer(true);
  assert.equal(f.st.host.__rompPaneHidden, false, "the observer's first word, published from releasePaint");
  assert.equal(f.st.catchUps, 1, "the observer's callback still runs the age pass's catch-up");
  f.observer(false);                                   // the shell hides the pane after the show; the viewport would still read its size
  assert.equal(f.st.host.__rompPaneHidden, true, "hidden after a first show: the case the probe misses");
  f.frame(2);
  assert.equal(f.st.paints, 1, "the paint is held while the pane is hidden");
  f.tab("hidden");
  assert.equal(f.st.host.__rompPaneHidden, true, "the hidden arm publishes (it releases nothing)");
  f.tab("visible");
  assert.equal(f.st.host.__rompPaneHidden, true, "the tab's return is not a show for a display:none pane");
  assert.equal(f.st.paints, 1, "and nothing paints for it");
  f.observer(true);
  assert.equal(f.st.host.__rompPaneHidden, false, "the re-show publishes on the observer's callback");
  assert.equal(f.st.paints, 2, "and settles the owed paint");
  f.tab("hidden"); assert.equal(f.st.host.__rompPaneHidden, true, "the tab hidden with the pane on screen");
  f.tab("visible"); assert.equal(f.st.host.__rompPaneHidden, false, "the return publishes on visibilitychange");
  assert.equal(typeof f.st.host.__rompPaneHidden, "boolean", "a boolean, the type the shim tests for");
});

// ── the FIRST paint on the phone (stage 0 of the reconnect design, 2026-09-18) ──
// The feed pane loads at boot behind the chat tab on the phone (exempt from the lazy panes: its socket feeds the shell's
// bell), and its first frame painted the whole board into a display:none iframe. Now the first paint is held too while the
// pane is off screen on the phone (paint-gate.ts firstPaintHeld); the frame is applied (mirrorBadges rings the bell from it,
// before render() as ever), and the shell's panes word on the pane's show releases the paint. The harness models
// applyFeedPayload's order (mirrorBadges, then the gated render) and the panes handler's release; the pins below hold
// feed.ts to it; the wiring run at the end lifts feed.ts's own lines with a phone stand-in for window.parent.
//
// What the harness PAINTS is the render's own plan, lifted from feed.ts (review round 2, 2026-09-19): viewScope, viewBase,
// viewFiltered, turnGroups, paintPlan and paintedKeyOf run under esbuild against the real feed-search and tag-lens modules,
// with the pane's filter state (the footer's session filter, the search box, the tag lens) stood in. Round 1's harness stamped
// one a:<itemId> per model card, the shape that hid the defect: a card the model holds but the view never paints (a
// delegation satellite, a filtered card, a turn-group member) was parked for a paint that could never land it, and the
// base's openSession fallback never fired.
type ModelAsk = Ask & { sid?: string; name?: string; satellite?: boolean; groupTitle?: string; turnId?: string; t?: number };
type Views = { tags?: { id: string; name: string; color: string; members: string[] }[] } | null;
type PlanState = { model: ModelAsk[]; onlySid: string | null; searchQ: string; metas: { sid: string; name: string }[]; lens: { all?: boolean; none?: boolean; tags?: string[] }; views: Views };
function liftedPlan() {
  const names = ["viewScope", "viewBase", "viewFiltered", "turnGroups", "paintPlan", "paintedKeyOf"];
  const src = names.map((n) => body(n)).join("\n");
  const js = requireCjs("esbuild").transformSync(src, { loader: "ts" }).code;
  const prelude = `
    const searchSids = M.searchSids, searchMatches = M.searchMatches, lensAll = M.lensAll, lensUnions = M.lensUnions, lensVisible = M.lensVisible;
    let asks = [], feedOnlySid = null, feedSearchQ = "", sessionsMeta = [], feedLens = { all: true }, feedTagViews = null;
    const bind = (st) => { asks = st.model; feedOnlySid = st.onlySid; feedSearchQ = st.searchQ; sessionsMeta = st.metas; feedLens = st.lens; feedTagViews = st.views; };
  `;
  const api = new Function("M", prelude + js + "\nreturn { plan: (st) => { bind(st); return paintPlan(asks); }, keyOf: (st, id) => { bind(st); return paintedKeyOf(id); } };")(
    { searchSids, searchMatches, lensAll, lensUnions, lensVisible }) as {
      plan(st: PlanState): { shown: ModelAsk[]; byTurn: Map<string, ModelAsk[]>; grouped: Set<string> }; keyOf(st: PlanState, id: string): string | null };
  /** the [data-key]s render() stamps for this state: g:<turnId> per group, a:<itemId> per shown ask outside every group (renderBody's two loops) */
  const keys = (st: PlanState) => { const p = api.plan(st); return Array.from(p.byTurn.keys()).map((t) => "g:" + t).concat(p.shown.filter((a) => !p.grouped.has(a.itemId)).map((a) => "a:" + a.itemId)); };
  return { plan: api.plan, keyOf: api.keyOf, keys };
}
const PLAN = liftedPlan();

function phoneFeed(opts: { phone?: boolean | undefined; probeHidden?: boolean } = {}) {
  const st = { hidden: false, intersecting: null as boolean | null, shellOn: undefined as boolean | undefined, revealShown: false,   // revealShown: the show override (D4), never the observer's variable
               phone: "phone" in opts ? opts.phone : true, probeHidden: opts.probeHidden ?? true,
               painted: 0, paints: 0, paintDirty: false, notified: [] as string[], model: [] as ModelAsk[],
               onlySid: null as string | null, searchQ: "", metas: [] as { sid: string; name: string }[], lens: { all: true } as PlanState["lens"], views: null as Views,   // the pane's filter state: the footer's session filter, the search box, the tag lens
               dom: [] as string[], jumped: [] as string[], opened: [] as string[], pendingRevealKey: null as string | null,   // dom: the [data-key] cards render() stamped (the lifted plan's keys); jumped: the cards scrolled to; opened: the openSession fallbacks posted
               host: {} as PaneHiddenHost, events: [] as string[], firstHoldTold: false, firstHoldReleased: false };   // host: where the pane's hidden word lands; events: the pane loader's hold events (D3)
  const seenNow = () => (st.revealShown ? true : st.intersecting);   // feed.ts seenNow: the paint's measure
  function mirrorBadges(asks: Ask[]) { for (const a of asks) if (a.column === "needsInput") st.notified.push(a.itemId); }   // one bell entry per card in trouble
  function render() {
    if (paintHeld(st.hidden, seenNow(), st.painted > 0) || firstPaintHeld(st.painted > 0, st.phone, st.shellOn, st.probeHidden, seenNow())) {
      st.paintDirty = true;
      if (st.painted === 0 && !st.firstHoldTold) { st.firstHoldTold = true; st.events.push("romp:firstpaintheld"); }   // feed.ts firstPaintHoldTold: once per hold
      return;
    }
    st.paints++; st.dom = PLAN.keys(st); st.painted = st.dom.length;   // what renderBody stamps, from the render's own plan (an empty board still paints: `.feed-empty` is the list's child)
    if (st.painted === 0) st.painted = 1;   // the empty board's own child (feed.ts appends `.feed-empty`), so the standing gate reads content after the first paint
  }
  function releasePaint() {
    publishPaneHidden(st.hidden, st.intersecting, st.host);   // the observer's word alone, never the override
    if (!paintReleased(st.paintDirty, st.hidden, seenNow())) return;
    st.paintDirty = false; render();
    if (st.firstHoldTold && !st.firstHoldReleased && !st.paintDirty) { st.firstHoldReleased = true; st.events.push("romp:firstpaintreleased"); }
    if (st.pendingRevealKey !== null && !st.paintDirty) { const k = st.pendingRevealKey; st.pendingRevealKey = null; if (st.dom.includes(k)) st.jumped.push(k); }   // feed.ts releasePaint's tail
  }
  /** the IntersectionObserver's callback over #feed-list, as feed.ts's watchFeedVisibility takes it */
  function observer(intersecting: boolean) {
    const was = st.intersecting;
    st.intersecting = intersecting;
    st.revealShown = false;
    if (was === true && !intersecting) st.pendingRevealKey = null;
    releasePaint();
  }
  /** the revealCard handler's wiring over paint-gate.ts's real revealDecision and feed.ts's lifted paintedKeyOf (the pins below hold feed.ts to the same call) */
  function revealCard(itemId: string, sid: string) {
    if (st.paintDirty && st.shellOn !== false) { st.revealShown = true; releasePaint(); }
    const key = "a:" + itemId;
    const target = st.dom.includes(key) ? key : null;
    const decision = revealDecision(!!target, st.paintDirty, PLAN.keyOf(st, itemId) === key, !!sid);
    st.pendingRevealKey = decision === "park" ? key : null;   // feed.ts: this gesture's park or none (D5: a second reveal replaces or drops the first, whatever road it takes)
    if (decision === "jump" && target) st.jumped.push(target);
    else if (decision === "open") st.opened.push(sid);
    return decision;
  }
  function applyFeedPayload(m: { asks: ModelAsk[] }) { st.model = m.asks; mirrorBadges(m.asks); render(); }
  /** the shell's panes word, as feed.ts's handler takes it */
  function panesWord(on: Record<string, boolean>) {
    const was = st.shellOn;
    st.shellOn = on.feed === true;
    if (was === true && !st.shellOn) st.pendingRevealKey = null;
    if (st.shellOn && st.paintDirty && st.phone === true) { st.revealShown = true; releasePaint(); }
  }
  /** the shell's synchronous show hook (window.__rompPaneShown, D3), run by the shell's show() in the tap's task */
  function shown() { st.shellOn = true; if (st.paintDirty && st.phone === true) { st.revealShown = true; releasePaint(); } }
  /** the render's plan for the current state (the lifted feed.ts functions): what the paint would stamp */
  function plan() { return PLAN.plan(st); }
  return { st, applyFeedPayload, releasePaint, panesWord, revealCard, observer, shown, plan };
}

test("T4: an off-screen feed on the phone applies its first frame without painting the board; mirrorBadges rings from it before any paint; the first show paints it", () => {
  const f = phoneFeed();   // hidden since load: the probe reads 0, the observer has not spoken, no word from the shell yet
  f.applyFeedPayload({ asks: [{ itemId: "g1", column: "needsInput" }, { itemId: "g2", column: "asks" }] });
  assert.equal(f.st.paints, 0, "the first frame is applied, not painted: nobody can see the pane");
  assert.equal(f.st.paintDirty, true, "a paint is owed");
  assert.deepEqual(f.st.notified, ["g1"], "the bell rang from the frame, before any paint");
  assert.equal(f.st.model.length, 2, "the model is the frame's");
  f.panesWord({ chat: true, feed: false });   // the shell's word on the pane's load: the chat tab is showing
  assert.equal(f.st.paints, 0, "the word says off screen: still held");
  f.applyFeedPayload({ asks: [{ itemId: "g1", column: "needsInput" }, { itemId: "g2", column: "asks" }, { itemId: "g3", column: "needsInput" }] });
  assert.equal(f.st.paints, 0, "a second frame while off screen: applied, not painted");
  assert.deepEqual(f.st.notified, ["g1", "g1", "g3"], "…and rings for it (the seen-set dedups in the real mirror)");
  f.panesWord({ chat: false, feed: true });   // the tap on the Feed tab: the shell re-tells in the same task
  assert.equal(f.st.paints, 1, "the first show paints, once, synchronously on the shell's word");
  assert.ok(f.st.dom.length > 0, "the lifted plan painted cards (a derivation that yields nothing must not pass the next line)");
  assert.deepEqual(f.st.dom, ["a:g1", "a:g2", "a:g3"], "the board is the newest frame's");
  assert.equal(f.st.paintDirty, false);
  f.releasePaint();   // the observer's callback follows the show: nothing more owed
  assert.equal(f.st.paints, 1);
});

test("T4, the boundaries: the shown tab paints at once; off the phone the first content paints through as before", () => {
  const shown = phoneFeed({ probeHidden: false });   // the phone left on the Feed tab: the iframe has a viewport and no word says otherwise
  shown.applyFeedPayload({ asks: [{ itemId: "g1", column: "asks" }] });
  assert.equal(shown.st.paints, 1, "the shown tab's first frame paints");
  const desktop = phoneFeed({ phone: false, probeHidden: true });   // the desktop grid: the shell's probe says false
  desktop.applyFeedPayload({ asks: [{ itemId: "g1", column: "asks" }] });
  assert.equal(desktop.st.paints, 1, "the desktop paints its first content whatever the probe says (the rail's hidden pane keeps paintHeld's rule)");
  const alone = phoneFeed({ phone: undefined, probeHidden: true });   // a standalone page, the VS Code webview: no shell probe
  alone.applyFeedPayload({ asks: [{ itemId: "g1", column: "asks" }] });
  assert.equal(alone.st.paints, 1, "no shell: unchanged");
  const wordFirst = phoneFeed({ probeHidden: false });   // the shell's word arrived before the first frame (the load tell) and says off screen: the word wins over a viewport
  wordFirst.panesWord({ chat: true, feed: false });
  wordFirst.applyFeedPayload({ asks: [{ itemId: "g1", column: "asks" }] });
  assert.equal(wordFirst.st.paints, 0, "the shell's word is the newer measure: held");
});

test("F2 (review round 1, 2026-09-19): a bell jump into a held, never-painted phone feed is decided from the paint plan: no openSession for a card the paint will stamp, and the paint the show lands reveals it", () => {
  const f = phoneFeed();   // the phone on the Chat tab; the feed hidden since load
  f.applyFeedPayload({ asks: [{ itemId: "g1", column: "needsInput" }, { itemId: "g2", column: "asks" }] });
  f.panesWord({ chat: true, feed: false });   // the shell's load-hook word
  assert.equal(f.st.paints, 0, "held");
  assert.ok(f.plan().shown.length > 0, "the plan shows the card (a derivation that yields nothing must not pass the next lines)");
  f.revealCard("g1", "11111111-2222-3333-4444-000000000101");   // the bell row for g1's card (the shell toggles the pane's rail flag, switches no tab, posts the jump)
  assert.deepEqual(f.st.opened, [], "no openSession: the paint will stamp the card (before this fix the empty DOM took the card-gone fallback and focused or revived the session)");
  assert.deepEqual(f.st.jumped, [], "nothing to scroll to yet: the board is unpainted");
  assert.equal(f.st.pendingRevealKey, "a:g1", "the jump waits for the paint");
  assert.equal(f.st.paints, 0, "no release attempt for a pane the shell's word has off screen (D4): the pane stays unpainted");
  f.panesWord({ chat: false, feed: true });   // the user taps the Feed tab
  assert.equal(f.st.paints, 1, "the show paints");
  assert.ok(f.st.dom.length > 0, "cards painted");
  assert.deepEqual(f.st.jumped, ["a:g1"], "…and the paint reveals the card the jump named");
  assert.equal(f.st.pendingRevealKey, null);
  f.revealCard("g9", "11111111-2222-3333-4444-000000000109");   // a card that left the board (cleared) with its session named
  assert.deepEqual(f.st.opened, ["11111111-2222-3333-4444-000000000109"], "a card absent from the model keeps the card-gone fallback");
  const g = phoneFeed();
  g.applyFeedPayload({ asks: [{ itemId: "g1", column: "asks" }] });
  g.panesWord({ chat: true, feed: false });
  g.revealCard("g7", "11111111-2222-3333-4444-000000000107");   // absent from the model AND unpainted: the fallback, as at the base
  assert.deepEqual(g.st.opened, ["11111111-2222-3333-4444-000000000107"]);
  assert.equal(g.st.pendingRevealKey, null);
  // the wiring: the handler's branch, the parked key, the release's tail, the shared helpers
  assert.match(SRC, /if \(m\.romp === "revealCard"\) \{[\s\S]*?if \(paintDirty && feedShellOn !== false\) \{ revealShown = true; releasePaint\(\); \}\n\s*const key = "a:" \+ String\(m\.itemId \|\| ""\);\n\s*unfoldThreadsFor\(new Set\(\[key\]\)\);\n\s*const target = cardByKey\(key\);[^\n]*\n(?:\s*\/\/[^\n]*\n)*\s*const decision = revealDecision\(!!target, paintDirty, paintedKeyOf\(String\(m\.itemId \|\| ""\)\) === key, !!m\.sid\);\n\s*pendingRevealKey = decision === "park" \? key : null;[^\n]*\n\s*if \(decision === "jump" && target\) \{\n\s*jumpToCard\(target\);\n\s*\} else if \(decision === "open"\) \{/,
    "the handler: the release attempt, the structural lookup, then paint-gate.ts's revealDecision over (found, paintDirty, the paint will stamp this key, a session named); the park is written or cleared BEFORE the arms (a second reveal replaces or drops an earlier park whatever road it takes, D5), then the jump and open arms; the decision itself is executed above and in paint-gate.test.ts");
  assert.match(SRC, /import \{ firstPaintHeld, viewportHiddenSinceLoad, revealDecision \} from "\.\/paint-gate";/);
  assert.match(SRC, /^let pendingRevealKey: string \| null = null;/m);
  assert.match(body("releasePaint"), /render\(\);\n\s*if \(firstHoldTold[^\n]*\n\s*\/\/[^\n]*\n\s*if \(pendingRevealKey !== null && !paintDirty\) \{ const k = pendingRevealKey; pendingRevealKey = null; const t = cardByKey\(k\); if \(t\) jumpToCard\(t\); \}\n\}/,
    "the release's tail reveals the parked card on the paint it waited for (after the loader's release event, D3)");
  assert.match(body("cardByKey"), /Array\.from\(document\.querySelectorAll\("\[data-key\]"\)\) as HTMLElement\[\]\)\.find\(\(c\) => c\.dataset\.key === key\) \|\| null/, "the structural match, never an interpolated selector (#940)");
  assert.equal((SRC.match(/pendingRevealKey = /g) || []).length, 4, "this gesture's park or none (before the arms, so a second reveal replaces or drops the first), consumed, and dropped on the pane's flip to hidden by either witness (the shell's word, the observer's): four writes (the declaration initialises it null); review round 2, D5");
});

test("HIGH-1 (review round 2, 2026-09-19): a reveal the paint will NOT stamp under its key takes the base's open road at the tap, under the hold: a satellite, a session-filtered card, a search miss, a lens-hidden card, a turn-group member", () => {
  const SID = "11111111-2222-3333-4444-000000000101", OTHER = "11111111-2222-3333-4444-000000000102";
  const held = () => { const f = phoneFeed(); f.panesWord({ chat: true, feed: false }); return f; };   // the phone on the Chat tab: the hold stands on the shell's word
  // (a) a delegation satellite: off the default board (viewScope hides it without its session's filter)
  const a = held();
  a.applyFeedPayload({ asks: [{ itemId: "s1", column: "asks", sid: SID, satellite: true }, { itemId: "g1", column: "asks", sid: OTHER }] });
  assert.equal(a.st.paints, 0, "held");
  assert.ok(a.plan().shown.length > 0, "the plan shows the board (g1)");
  assert.equal(PLAN.keyOf(a.st, "s1"), null, "…and paints the satellite under no key");
  assert.equal(a.revealCard("s1", SID), "open");
  assert.deepEqual([a.st.opened, a.st.pendingRevealKey], [[SID], null], "the bell row for the satellite opens its session at the tap, as the base did; nothing is parked");
  // (b) the footer's session filter set to another session hides the card
  const b = held(); b.st.onlySid = OTHER;
  b.applyFeedPayload({ asks: [{ itemId: "g1", column: "asks", sid: SID }, { itemId: "g2", column: "asks", sid: OTHER }] });
  assert.deepEqual(PLAN.keys(b.st), ["a:g2"], "the filter shows the other session's card alone (the plan is not empty: the filtered card is what is missing)");
  assert.equal(b.revealCard("g1", SID), "open");
  assert.deepEqual([b.st.opened, b.st.pendingRevealKey], [[SID], null]);
  // (c) a search query that matches neither the session's name nor the card's own label
  const c = held(); c.st.searchQ = "zzz-no-such"; c.st.metas = [{ sid: SID, name: "web" }];
  c.applyFeedPayload({ asks: [{ itemId: "g1", column: "asks", sid: SID, name: "web" }] });
  assert.equal(PLAN.plan(c.st).shown.length, 0, "the search hides every card (a literal: the view is legitimately empty here)");
  assert.equal(c.revealCard("g1", SID), "open");
  assert.deepEqual([c.st.opened, c.st.pendingRevealKey], [[SID], null]);
  // (d) the tag lens hides the card's session; a needs-you card passes the lens (viewBase's interrupt rule) and is parked
  const lens = { tags: ["other-tag"] }, views = { tags: [{ id: "t1", name: "home", color: "#1EA1EB", members: [SID] }] };
  const d = held(); d.st.lens = lens; d.st.views = views;
  d.applyFeedPayload({ asks: [{ itemId: "g1", column: "asks", sid: SID }] });
  assert.equal(PLAN.plan(d.st).shown.length, 0, "the lens hides the session's working card");
  assert.equal(d.revealCard("g1", SID), "open");
  assert.deepEqual([d.st.opened, d.st.pendingRevealKey], [[SID], null]);
  const d2 = held(); d2.st.lens = lens; d2.st.views = views;
  d2.applyFeedPayload({ asks: [{ itemId: "g1", column: "needs_input", sid: SID }] });
  assert.deepEqual(PLAN.keys(d2.st), ["a:g1"], "needs-you passes the lens");
  assert.equal(d2.revealCard("g1", SID), "park", "…so the same card in needs-you is parked for the paint");
  assert.deepEqual([d2.st.opened, d2.st.pendingRevealKey], [[], "a:g1"]);
  d2.panesWord({ chat: false, feed: true });
  assert.deepEqual(d2.st.jumped, ["a:g1"], "and the show's paint reveals it");
  // (e) two cards sharing a typed turn fold into one group card, g:<turnId>: a member is never stamped a:<itemId>
  const e = held();
  e.applyFeedPayload({ asks: [{ itemId: "m1", column: "asks", sid: SID, groupTitle: "the turn", turnId: "T1", t: 1 }, { itemId: "m2", column: "asks", sid: SID, groupTitle: "the turn", turnId: "T1", t: 2 }] });
  assert.deepEqual(PLAN.keys(e.st), ["g:T1"], "the plan paints the group alone");
  assert.equal(PLAN.keyOf(e.st, "m1"), "g:T1", "a member's painted key is the group's");
  assert.equal(e.revealCard("m1", SID), "open", "the reveal names a:m1, which the paint never stamps: the base's fallback (a card folded into a group opens its session), at the tap");
  assert.deepEqual([e.st.opened, e.st.pendingRevealKey], [[SID], null]);
  // (f) a plain card: parked, revealed by the show (today's F2, unchanged)
  const f = held();
  f.applyFeedPayload({ asks: [{ itemId: "g1", column: "asks", sid: SID }] });
  assert.equal(f.revealCard("g1", SID), "park");
  f.panesWord({ chat: false, feed: true });
  assert.deepEqual([f.st.opened, f.st.jumped], [[], ["a:g1"]]);
  // the wiring: the handler asks paintedKeyOf; renderBody consumes paintPlan's object (one derivation, no second viewFiltered/turnGroups pass)
  assert.match(SRC, /const decision = revealDecision\(!!target, paintDirty, paintedKeyOf\(String\(m\.itemId \|\| ""\)\) === key, !!m\.sid\);/, "the handler's third argument is the paint plan's answer for this key");
  const rb = body("renderBody");
  assert.match(rb, /\n  const plan = paintPlan\(asks\);\n  const shown = plan\.shown, byTurn = plan\.byTurn, grouped = plan\.grouped;\n  for \(const \[tid, members\] of byTurn\) \{\n    const g = buildGroup\(tid, members\);/, "renderBody paints from paintPlan's object");
  assert.doesNotMatch(rb, /viewFiltered\(|turnGroups\(/, "…and derives neither view nor groups a second time");
  assert.equal(SRC.split("paintPlan(").length - 1, 3, "three sites: the definition, renderBody, paintedKeyOf");
  assert.match(body("paintedKeyOf"), /const plan = paintPlan\(asks\);\n\s*const a = plan\.shown\.find\(\(x\) => x\.itemId === itemId\);\n\s*if \(!a\) return null;\n\s*return plan\.grouped\.has\(itemId\) \? "g:" \+ a\.turnId : "a:" \+ itemId;/, "paintedKeyOf answers from the same plan");
  assert.match(body("paintPlan"), /const shown = viewFiltered\(list\);\n\s*const byTurn = turnGroups\(shown\);/, "the plan is the display view and its groups, the lines renderBody used to run inline");
});

test("feed.ts wires the first-paint hold: the shell's word and the two probes beside the observer's word, and the panes handler releases on the phone's show", () => {
  assert.match(SRC, /let feedShellOn: boolean \| undefined;\nfunction parentMobile\(\): boolean \| undefined \{\n\s*try \{ const p = window\.parent as unknown as \{ __rompMobileOn\?: unknown \}; return \(window\.parent !== window && typeof p\.__rompMobileOn === "function"\) \? !!\(p\.__rompMobileOn as \(\) => unknown\)\(\) : undefined; \} catch \{ return undefined; \}\n\}/,
    "the shell's layout probe, read live as the kernel's pane shim reads it; the zero-viewport probe is paint-gate.ts's viewportHiddenSinceLoad over the page's window (feed-age.test.ts pins that feed.ts itself carries no probe)");
  assert.doesNotMatch(SRC, /window\.innerWidth === 0/, "no probe text in feed.ts: the standing gate never reads one (feed-age.test.ts), and the first-paint hold reads it through paint-gate.ts");
  assert.match(SRC, /if \(m\.romp === "panes"\) \{\n(?:\s*\/\/[^\n]*\n)*\s*if \(m\.on && typeof m\.on === "object"\) \{\n\s*const was = feedShellOn;\n\s*feedShellOn = m\.on\.feed === true;\n\s*if \(was === true && !feedShellOn\) pendingRevealKey = null;[^\n]*\n\s*if \(feedShellOn && paintDirty && parentMobile\(\) === true\) \{ revealShown = true; releasePaint\(\); \}\n\s*\}\n\s*return;\n\s*\}/,
    "the panes word: this pane's on-screen word; a flip to hidden drops a parked jump (D5); on the phone's show the release of the owed paint through the show override (D4; the word stands in for the observer's, the revealCard precedent)");
  assert.match(SRC, /^\(window as unknown as \{ __rompPaneShown\?: \(\) => void \}\)\.__rompPaneShown = \(\) => \{ feedShellOn = true; if \(paintDirty && parentMobile\(\) === true\) \{ revealShown = true; releasePaint\(\); \} \};/m,
    "the shell's synchronous show hook (D3): the same body as the panes handler's show arm, run in the tap's task by kernel _LANDING_MOBILE_JS show()");
  assert.ok(SRC.indexOf('if (m.romp === "panes") {') < SRC.indexOf('if (m.romp === "revealCard") {'), "…ahead of the bell jump (on the desktop the shell posts the jump after the show's word; on the phone a jump into a held board is decided from the model, the F2 case above)");
  const apply = body("applyFeedPayload");
  assert.ok(apply.indexOf("mirrorBadges(") < apply.indexOf("\n  render();\n"), "the bell mirror runs before the gated render: it rings from a frame whose paint is held");
});

test("run: feed.ts's own gate over a phone stand-in holds the first frame of a pane hidden since load and paints it when the observer sees the iframe", () => {
  // the wiring slice, with window.parent the shell's probe (phone) and a zero viewport (hidden since load)
  const f = feedWiring({ parentProbe: () => true, innerWidth: 0, innerHeight: 0 });
  f.frame(3);
  assert.equal(f.st.paints, 0, "the first frame of an off-screen pane on the phone is applied, not painted");
  f.observer(false);   // the observer's first word: off screen (the iframe is display:none)
  assert.equal(f.st.paints, 0);
  f.viewport(390, 700); f.observer(true);    // the tap: the iframe shows (its viewport is its size again) and the observer re-measures
  assert.equal(f.st.paints, 1, "the first show paints, on the observer's own event");
  assert.equal(f.st.painted, 3);
  const d = feedWiring({ parentProbe: () => false, innerWidth: 0, innerHeight: 0 });   // the desktop: the same zero viewport, no hold
  d.frame(2);
  assert.equal(d.st.paints, 1, "the desktop's first content paints through as before");
  const s = feedWiring({ parentProbe: () => true, innerWidth: 390, innerHeight: 700 });   // the phone left on the Feed tab
  s.frame(2);
  assert.equal(s.st.paints, 1, "the shown tab paints its first frame at once");
});

// ── review round 2 (2026-09-19): the show paints synchronously and holds the pane loader (D3); no reveal writes the observer's
// variable (D4); the parked jump retires on the pane's next visibility change (D5) ──
test("D3: the shell's show hook paints the held first board in the tap's own task, and the pane loader is told once per hold and once at the release", () => {
  const f = phoneFeed();   // the phone on the Chat tab, the feed hidden since load
  f.applyFeedPayload({ asks: [{ itemId: "g1", column: "asks" }] });
  f.panesWord({ chat: true, feed: false });
  f.applyFeedPayload({ asks: [{ itemId: "g1", column: "asks" }, { itemId: "g2", column: "asks" }] });
  assert.equal(f.st.paints, 0, "two frames applied, none painted");
  assert.deepEqual(f.st.events, ["romp:firstpaintheld"], "the pane loader is told ONCE that the first paint is held (its 30 s failsafe stands down: nobody can see the sheet)");
  f.shown();   // the tap on the Feed tab: the shell's show() calls the hook before its re-tell
  assert.equal(f.st.paints, 1, "the first paint lands synchronously in the show's task, before any panes word");
  assert.ok(f.st.dom.length > 0, "cards painted");
  assert.deepEqual(f.st.events, ["romp:firstpaintheld", "romp:firstpaintreleased"], "…and the loader's backstop resumes, told once");
  f.panesWord({ chat: false, feed: true });   // the shell's re-tell, a later task
  f.observer(true);                            // the observer's re-measure, a rendering step later
  assert.equal(f.st.paints, 1, "the word and the observer that follow the show paint nothing more");
  assert.deepEqual(f.st.events, ["romp:firstpaintheld", "romp:firstpaintreleased"], "no second event");
  // a release that RE-HOLDS dispatches nothing: the browser tab's return with the pane still off screen on the shell's word
  const g = phoneFeed();
  g.applyFeedPayload({ asks: [{ itemId: "g1", column: "asks" }] });
  g.panesWord({ chat: true, feed: false });
  g.st.hidden = true; g.st.hidden = false; g.releasePaint();   // visibilitychange -> visible: paintReleased says yes (the observer is unspoken), render() re-holds on the word
  assert.equal(g.st.paints, 0, "re-held");
  assert.deepEqual(g.st.events, ["romp:firstpaintheld"], "a release that painted nothing re-arms no backstop (the sheet would fade over an empty list)");
  // the desktop and a standalone page: no hold, so no events
  const d = phoneFeed({ phone: false });
  d.applyFeedPayload({ asks: [{ itemId: "g1", column: "asks" }] });
  assert.deepEqual([d.st.paints, d.st.events], [1, []], "off the phone the first content paints through and the loader hears nothing");
});

test("D4: a reveal into a pane the shell has off screen leaves the observer's word and the published hidden word alone and paints nothing into the hidden iframe; a desktop reveal releases synchronously and the observer spends the override", () => {
  const f = phoneFeed({ probeHidden: false });   // the phone left on the Feed tab
  f.applyFeedPayload({ asks: [{ itemId: "g1", column: "asks" }] });
  assert.equal(f.st.paints, 1, "the shown tab paints its first frame");
  f.observer(true);
  assert.equal(f.st.host.__rompPaneHidden, false, "the observer's first word: on screen");
  f.panesWord({ chat: true, feed: false }); f.observer(false);   // the user taps the Chat tab: the shell's word, then the observer's
  assert.equal(f.st.host.__rompPaneHidden, true, "hidden after a first show");
  f.applyFeedPayload({ asks: [{ itemId: "g1", column: "asks" }, { itemId: "g2", column: "asks" }] });
  assert.equal(f.st.paints, 1, "a frame while hidden is applied, not painted");
  assert.equal(f.revealCard("g2", "11111111-2222-3333-4444-000000000102"), "park", "the bell row for g2 (the shell switches no tab on the phone)");
  assert.equal(f.st.intersecting, false, "the observer's variable is untouched (before this fix the arm wrote true into it and nothing restored it)");
  assert.equal(f.st.host.__rompPaneHidden, true, "the published word still says hidden: the shim is not told a hidden pane is on screen");
  assert.equal(f.st.revealShown, false, "no override for a pane the shell has off screen");
  assert.equal(f.st.paints, 1, "nothing painted into the display:none iframe");
  f.applyFeedPayload({ asks: [{ itemId: "g1", column: "asks" }, { itemId: "g2", column: "asks" }, { itemId: "g3", column: "asks" }] });
  assert.equal(f.st.paints, 1, "…and the next push repaints nothing either (the defect: every push repainted the board into the hidden pane)");
  f.panesWord({ chat: false, feed: true });   // the show
  assert.equal(f.st.paints, 2, "the show paints once");
  assert.deepEqual(f.st.jumped, ["a:g2"], "…and lands the parked jump");
  f.observer(true);
  assert.equal(f.st.revealShown, false, "the observer's callback spends the override");
  // the desktop: the shell toggles the pane on (its word true) and posts the jump in the same task, before the observer re-measures
  const d = phoneFeed({ phone: false, probeHidden: false });
  d.applyFeedPayload({ asks: [{ itemId: "g1", column: "asks" }] });
  d.observer(true); d.panesWord({ chat: true, feed: true });
  d.observer(false);   // the rail toggled the pane off (display:none): the observer's word
  d.applyFeedPayload({ asks: [{ itemId: "g1", column: "asks" }, { itemId: "g2", column: "asks" }] });
  assert.equal(d.st.paints, 1, "held while off");
  assert.equal(d.revealCard("g2", "11111111-2222-3333-4444-000000000102"), "jump", "the bell click toggled the pane on (the word stands at true): the reveal releases synchronously and finds the card, the base's behaviour");
  assert.equal(d.st.paints, 2, "one synchronous paint");
  assert.equal(d.st.intersecting, false, "…through the override, not the observer's variable");
  assert.equal(d.st.revealShown, true, "the override stands until the observer speaks");
  d.observer(true);
  assert.equal(d.st.revealShown, false, "the observer's next callback clears it");
  d.observer(false); d.applyFeedPayload({ asks: [{ itemId: "g1", column: "asks" }] });
  assert.equal(d.st.paints, 2, "a later hide holds again (the override did not outlive the observer's word)");
});

test("D5: the parked jump retires on the pane's next visibility change: the show consumes it, a flip to hidden drops it, a second reveal replaces it, a re-tell of the same word changes nothing", () => {
  const SID = "11111111-2222-3333-4444-000000000101";
  // the shell re-tells the same off-screen word on its socket events: the park stands; the show consumes it
  const f = phoneFeed();
  f.applyFeedPayload({ asks: [{ itemId: "g1", column: "asks", sid: SID }] });
  f.panesWord({ chat: true, feed: false });
  assert.equal(f.revealCard("g1", SID), "park");
  for (let i = 0; i < 3; i++) f.panesWord({ chat: true, feed: false });   // the shell's re-tells (a socket open, a close, a link flip)
  assert.equal(f.st.pendingRevealKey, "a:g1", "a re-tell of the same word is not a visibility change: the park stands");
  f.panesWord({ chat: false, feed: true });
  assert.deepEqual([f.st.pendingRevealKey, f.st.jumped], [null, ["a:g1"]], "the show that follows the reveal consumes it");
  // a park made while the pane is shown but the browser tab is hidden; the shell's word then flips the pane to hidden: dropped
  const g = phoneFeed({ probeHidden: false });
  g.applyFeedPayload({ asks: [{ itemId: "g1", column: "asks", sid: SID }] });
  g.observer(true); g.panesWord({ chat: false, feed: true });
  g.st.hidden = true;   // the browser tab goes to the background with the Feed tab shown
  g.applyFeedPayload({ asks: [{ itemId: "g1", column: "asks", sid: SID }, { itemId: "g2", column: "asks", sid: SID }] });
  assert.equal(g.revealCard("g2", SID), "park", "a reveal while the tab is hidden parks (the release attempt waits for the tab)");
  g.panesWord({ chat: true, feed: false });   // a relay's tab switch while away: the pane is hidden now
  assert.equal(g.st.pendingRevealKey, null, "the flip to hidden drops the park: the next show is not this gesture's");
  g.st.hidden = false; g.releasePaint(); g.panesWord({ chat: false, feed: true }); g.observer(true);
  assert.deepEqual(g.st.jumped, [], "…so the later show jumps nothing");
  // the observer's flip to hidden drops it too
  const h = phoneFeed({ probeHidden: false });
  h.applyFeedPayload({ asks: [{ itemId: "g1", column: "asks", sid: SID }] });
  h.observer(true); h.panesWord({ chat: false, feed: true });
  h.st.hidden = true;
  h.applyFeedPayload({ asks: [{ itemId: "g1", column: "asks", sid: SID }, { itemId: "g2", column: "asks", sid: SID }] });
  assert.equal(h.revealCard("g2", SID), "park");
  h.observer(false);
  assert.equal(h.st.pendingRevealKey, null, "the observer's hide after a show drops it");
  // two reveals in a row: the second's key stands alone
  const k = phoneFeed();
  k.applyFeedPayload({ asks: [{ itemId: "g1", column: "asks", sid: SID }, { itemId: "g2", column: "asks", sid: SID }] });
  k.panesWord({ chat: true, feed: false });
  k.revealCard("g1", SID); k.revealCard("g2", SID);
  assert.equal(k.st.pendingRevealKey, "a:g2", "a second reveal replaces the first");
  k.panesWord({ chat: false, feed: true });
  assert.deepEqual(k.st.jumped, ["a:g2"]);
  // a second reveal that takes a road other than the park (review round 2 closeout, D5): the first park is dropped, not left for the next
  // show. Two bell-row taps on the Chat tab, the second on a delegation satellite the paint will not stamp (the open road), then a Feed tap
  const n = phoneFeed();
  n.applyFeedPayload({ asks: [{ itemId: "g1", column: "asks", sid: SID }, { itemId: "s1", column: "asks", sid: SID, satellite: true }] });
  n.panesWord({ chat: true, feed: false });
  assert.equal(n.revealCard("g1", SID), "park");
  assert.equal(n.revealCard("s1", SID), "open", "the satellite takes the open road at the tap");
  assert.equal(n.st.pendingRevealKey, null, "…and the older gesture's park is dropped (before: 'a:g1' stood, and the next show jumped to a card the user had moved on from)");
  n.panesWord({ chat: false, feed: true });
  assert.deepEqual(n.st.jumped, [], "the show jumps nothing");
  // the same on feed.ts's own handler lines (revealWiring lifts the revealCard block)
  const L = revealWiring({ paintDirty: true, shellOn: false, dom: [], keyOf: (id) => (id === "g1" || id === "g2" ? "a:" + id : null) });
  L.reveal("g1", SID);
  assert.equal(L.pending(), "a:g1", "parked on feed.ts's own line");
  L.reveal("s1", SID);
  assert.equal(L.pending(), null, "a second reveal the paint will not stamp drops the park on feed.ts's own lines");
  assert.deepEqual(L.st.posted.map((p) => p.type), ["openSession"], "…and takes the open road");
  assert.deepEqual(L.st.gesture, [true], "the reader's gesture stands behind the openSession post");
  L.reveal("g1", SID); L.reveal("g2", SID);
  assert.equal(L.pending(), "a:g2", "a second park replaces the first on feed.ts's own lines");
  assert.equal(L.st.released, 0, "no release attempt while the shell's word says the pane is off screen");
  const J = revealWiring({ paintDirty: false, shellOn: true, dom: ["a:g1"], keyOf: (id) => "a:" + id });
  J.reveal("g1", SID);
  assert.deepEqual([J.pending(), J.st.jumped], [null, ["a:g1"]], "a found card under a painted board jumps and leaves no park");
});

// feed.ts's revealCard handler, lifted and run (review round 2 closeout, D5): the block from `if (m.romp === "revealCard") {` to its
// `return;` is feed.ts's text, transpiled at run time, with its collaborators stood in (the release attempt counted, the structural
// lookup over a list of painted keys, the plan's answer per id, the openSession post recorded with the gesture flag it rode on)
function revealWiring(opts: { paintDirty: boolean; shellOn: boolean | undefined; dom: string[]; keyOf: (id: string) => string | null }) {
  const start = 'if (m.romp === "revealCard") {', endMark = '\n  if (m.type === "feedDelta") {';
  const a = SRC.indexOf(start), b = SRC.indexOf(endMark, a);
  assert.ok(a > 0 && b > a, "the reveal handler's anchors moved; re-anchor");
  const block = SRC.slice(a, b);
  assert.match(block, /\n    return;\n  \}$/, "the block ends with the handler's own return");
  const js = requireCjs("esbuild").transformSync("function onMessage(m) {\n" + block + "\n}", { loader: "ts" }).code;
  const st = { released: 0, jumped: [] as string[], posted: [] as { type: string }[], gesture: [] as boolean[], ...opts };
  const prelude = `
    let paintDirty = S.paintDirty, feedShellOn = S.shellOn, revealShown = false, pendingRevealKey = null, frameGesture = false;
    const releasePaint = () => { S.released++; };
    const unfoldThreadsFor = () => {};
    const cardByKey = (k) => (S.dom.includes(k) ? { key: k } : null);
    const jumpToCard = (t) => { S.jumped.push(t.key); };
    const paintedKeyOf = (id) => S.keyOf(id);
    const vscodeApi = { postMessage: (m) => { S.posted.push(m); S.gesture.push(frameGesture); } };
    const revealDecision = P.revealDecision;
  `;
  const api = new Function("P", "S", prelude + js + "\nreturn { onMessage, pending: () => pendingRevealKey };")({ revealDecision }, st) as { onMessage(m: unknown): void; pending(): string | null };
  return { st, pending: api.pending, reveal(itemId: string, sid: string) { api.onMessage({ romp: "revealCard", itemId, sid, gesture: true }); } };
}

test("run: feed.ts's own lines take the shell's show hook: the held first frame paints synchronously, the loader's two events fire once each, and the observer's callback afterwards paints nothing more", () => {
  const f = feedWiring({ parentProbe: () => true, innerWidth: 0, innerHeight: 0 });   // the phone, the feed hidden since load
  f.frame(3);
  f.frame(4);
  assert.equal(f.st.paints, 0, "held");
  assert.deepEqual(f.events, ["romp:firstpaintheld"], "told once across two held frames");
  f.observer(false);   // the observer's first word over the display:none iframe: off screen (review round 2 closeout, D4: with no word yet the paint proceeds on null whether or not the override is read, so the read side had no executed witness)
  assert.equal(f.st.host.__rompPaneHidden, true, "published hidden");
  assert.equal(f.st.paints, 0, "still held");
  f.viewport(390, 700); f.shown();   // the tap: the shell shows the iframe and calls the hook in the same task; the observer's word still says hidden, so the paint rides the override alone
  assert.equal(f.st.paints, 1, "painted synchronously, through the show override over the observer's standing hidden word (render()'s gate reads seenNow())");
  assert.equal(f.st.painted, 4);
  assert.deepEqual(f.events, ["romp:firstpaintheld", "romp:firstpaintreleased"], "the backstop resumes once");
  f.observer(true);
  assert.equal(f.st.paints, 1, "the observer's re-measure owes nothing");
  assert.equal(f.st.host.__rompPaneHidden, false, "…and publishes on screen");
  f.observer(false); f.frame(5);   // the user taps another tab: the observer says hidden; a frame arrives
  assert.equal(f.st.paints, 1, "held: the show override did not outlive the observer's word (D4: its callback clears the flag)");
  assert.equal(f.st.host.__rompPaneHidden, true);
  f.shown();   // the Feed tab tapped again: the hook lands the paint owed while hidden in the tap's task, before the observer has re-measured (review round 2 closeout: the standing gate over a board WITH content consults the measure, so this is where render()'s gate must read the override, not the observer's variable)
  assert.equal(f.st.paints, 2, "the re-show paints synchronously through the override over the observer's standing hidden word");
  assert.equal(f.st.painted, 5, "…the frame that arrived while hidden");
  assert.deepEqual(f.events, ["romp:firstpaintheld", "romp:firstpaintreleased"], "the loader's events are the first hold's alone");
  f.observer(true);
  assert.equal(f.st.paints, 2, "the observer's re-measure owes nothing");
});
