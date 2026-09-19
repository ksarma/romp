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
  assert.match(SRC, /function render\(\) \{\n  const list = document\.getElementById\("feed-list"\)!;\n  if \(!feedWatching\) \{ feedWatching = true; watchFeedVisibility\(list\); \}\n  if \(paintHeld\(document\.hidden, feedIntersecting, list\.childElementCount > 0\) \|\| firstPaintHeld\(list\.childElementCount > 0, parentMobile\(\), feedShellOn, viewportHiddenSinceLoad\(window\), feedIntersecting\)\) \{ paintDirty = true; return; \}\n  pruneTip\(\);/,
    "the gate precedes every paint-side step (pruneTip, applyFollowMove, the footer, the columns); the phone's first-paint hold rides the same line (stage 0, 2026-09-18)");
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
  assert.match(rel, /function releasePaint\(\): void \{\n\s*publishPaneHidden\(document\.hidden, feedIntersecting\);\n\s*if \(!paintReleased\(paintDirty, document\.hidden, feedIntersecting\)\) return;\n\s*paintDirty = false;\n\s*skipFlipOnce = true;\n\s*render\(\);/,
    "the release publishes the pane's word for the kernel's pane shim first (paint-gate.ts publishPaneHidden), then settles the owed paint");
  assert.doesNotMatch(rel, /requestAnimationFrame|setTimeout|queueMicrotask/, "the release paints synchronously: the earliest fresh frame after the compositor's cached one");
});

test("BOTH release events run the same release: visibilitychange→visible and the observer's callback", () => {
  assert.match(SRC, /document\.addEventListener\("visibilitychange", \(\) => \{ if \(!document\.hidden\) releasePaint\(\); \}\);/);
  assert.match(SRC, /document\.addEventListener\("visibilitychange", \(\) => \{ if \(document\.hidden\) publishPaneHidden\(true, feedIntersecting\); \}\);/,
    "the hidden arm releases nothing, so it publishes the pane's word itself");
  assert.equal(SRC.split("publishPaneHidden(").length - 1, 2, "two publish sites, both on the gate's events; no timer");
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
  const fakeWindow: any = { innerWidth: win.innerWidth ?? 800, innerHeight: win.innerHeight ?? 600 };
  fakeWindow.parent = win.parentProbe ? { __rompMobileOn: win.parentProbe } : fakeWindow;
  hideEdges(fakeWindow);
  const api = new Function("P", "S", "document", "IntersectionObserver", "window", prelude + js + "\nreturn { render, releasePaint };")(
    { paintHeld, paintReleased, publishPaneHidden, firstPaintHeld, viewportHiddenSinceLoad }, st, fakeDocument, FakeObserver, fakeWindow) as { render(): void; releasePaint(): void };
  return {
    st,
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
function phoneFeed(opts: { phone?: boolean | undefined; probeHidden?: boolean } = {}) {
  const st = { hidden: false, intersecting: null as boolean | null, shellOn: undefined as boolean | undefined,
               phone: "phone" in opts ? opts.phone : true, probeHidden: opts.probeHidden ?? true,
               painted: 0, paints: 0, paintDirty: false, notified: [] as string[], model: [] as Ask[],
               dom: [] as string[], jumped: [] as string[], opened: [] as string[], pendingRevealKey: null as string | null };   // dom: the [data-key] cards render() stamped; jumped: the cards scrolled to; opened: the openSession fallbacks posted
  function mirrorBadges(asks: Ask[]) { for (const a of asks) if (a.column === "needsInput") st.notified.push(a.itemId); }   // one bell entry per card in trouble
  function render() {
    if (paintHeld(st.hidden, st.intersecting, st.painted > 0) || firstPaintHeld(st.painted > 0, st.phone, st.shellOn, st.probeHidden, st.intersecting)) { st.paintDirty = true; return; }
    st.paints++; st.painted = st.model.length; st.dom = st.model.map((a) => "a:" + a.itemId);
  }
  function releasePaint() {
    if (!paintReleased(st.paintDirty, st.hidden, st.intersecting)) return;
    st.paintDirty = false; render();
    if (st.pendingRevealKey !== null && !st.paintDirty) { const k = st.pendingRevealKey; st.pendingRevealKey = null; if (st.dom.includes(k)) st.jumped.push(k); }   // feed.ts releasePaint's tail
  }
  /** the revealCard handler's wiring over paint-gate.ts's real revealDecision (the pins below hold feed.ts to the same call) */
  function revealCard(itemId: string, sid: string) {
    if (st.paintDirty) { st.intersecting = true; releasePaint(); }
    const key = "a:" + itemId;
    const target = st.dom.includes(key) ? key : null;
    const decision = revealDecision(!!target, st.paintDirty, st.model.some((a) => a.itemId === itemId), !!sid);
    if (decision === "jump" && target) st.jumped.push(target);
    else if (decision === "park") st.pendingRevealKey = key;
    else if (decision === "open") st.opened.push(sid);
  }
  function applyFeedPayload(m: Payload) { st.model = m.asks; mirrorBadges(m.asks); render(); }
  /** the shell's panes word, as feed.ts's handler takes it */
  function panesWord(on: Record<string, boolean>) {
    st.shellOn = on.feed === true;
    if (st.shellOn && st.paintDirty && st.phone === true) { st.intersecting = true; releasePaint(); }
  }
  return { st, applyFeedPayload, releasePaint, panesWord, revealCard };
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
  assert.equal(f.st.painted, 3, "the board is the newest frame's");
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

test("F2 (review round 1, 2026-09-19): a bell jump into a held, never-painted phone feed is decided from the model: no openSession for a card that exists, and the paint the show lands reveals it", () => {
  const f = phoneFeed();   // the phone on the Chat tab; the feed hidden since load
  f.applyFeedPayload({ asks: [{ itemId: "g1", column: "needsInput" }, { itemId: "g2", column: "asks" }] });
  f.panesWord({ chat: true, feed: false });   // the shell's load-hook word
  assert.equal(f.st.paints, 0, "held");
  f.revealCard("g1", "11111111-2222-3333-4444-000000000101");   // the bell row for g1's card (the shell toggles the pane's rail flag, switches no tab, posts the jump)
  assert.deepEqual(f.st.opened, [], "no openSession: the card exists in the model (before this fix the empty DOM took the card-gone fallback and focused or revived the session)");
  assert.deepEqual(f.st.jumped, [], "nothing to scroll to yet: the board is unpainted");
  assert.equal(f.st.pendingRevealKey, "a:g1", "the jump waits for the paint");
  assert.equal(f.st.paints, 0, "the release attempt re-held on the shell's word: the pane stays unpainted off screen");
  f.panesWord({ chat: false, feed: true });   // the user taps the Feed tab
  assert.equal(f.st.paints, 1, "the show paints");
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
  assert.match(SRC, /if \(m\.romp === "revealCard"\) \{[\s\S]*?if \(paintDirty\) \{ feedIntersecting = true; releasePaint\(\); \}\n\s*const key = "a:" \+ String\(m\.itemId \|\| ""\);\n\s*unfoldThreadsFor\(new Set\(\[key\]\)\);\n\s*const target = cardByKey\(key\);[^\n]*\n(?:\s*\/\/[^\n]*\n)*\s*const decision = revealDecision\(!!target, paintDirty, asks\.some\(\(a\) => a\.itemId === String\(m\.itemId \|\| ""\)\), !!m\.sid\);\n\s*if \(decision === "jump" && target\) \{\n\s*jumpToCard\(target\);\n\s*\} else if \(decision === "park"\) \{\n\s*pendingRevealKey = key;\n\s*\} else if \(decision === "open"\) \{/,
    "the handler: the release attempt, the structural lookup, then paint-gate.ts's revealDecision over (found, paintDirty, in the model, a session named) and its three arms; the decision itself is executed above and in paint-gate.test.ts");
  assert.match(SRC, /import \{ firstPaintHeld, viewportHiddenSinceLoad, revealDecision \} from "\.\/paint-gate";/);
  assert.match(SRC, /^let pendingRevealKey: string \| null = null;/m);
  assert.match(body("releasePaint"), /render\(\);\n\s*\/\/[^\n]*\n\s*if \(pendingRevealKey !== null && !paintDirty\) \{ const k = pendingRevealKey; pendingRevealKey = null; const t = cardByKey\(k\); if \(t\) jumpToCard\(t\); \}\n\}/,
    "the release's tail reveals the parked card on the paint it waited for");
  assert.match(body("cardByKey"), /Array\.from\(document\.querySelectorAll\("\[data-key\]"\)\) as HTMLElement\[\]\)\.find\(\(c\) => c\.dataset\.key === key\) \|\| null/, "the structural match, never an interpolated selector (#940)");
  assert.equal((SRC.match(/pendingRevealKey = /g) || []).length, 2, "parked and consumed: two writes (the declaration initialises it null)");
});

test("feed.ts wires the first-paint hold: the shell's word and the two probes beside the observer's word, and the panes handler releases on the phone's show", () => {
  assert.match(SRC, /let feedShellOn: boolean \| undefined;\nfunction parentMobile\(\): boolean \| undefined \{\n\s*try \{ const p = window\.parent as unknown as \{ __rompMobileOn\?: unknown \}; return \(window\.parent !== window && typeof p\.__rompMobileOn === "function"\) \? !!\(p\.__rompMobileOn as \(\) => unknown\)\(\) : undefined; \} catch \{ return undefined; \}\n\}/,
    "the shell's layout probe, read live as the kernel's pane shim reads it; the zero-viewport probe is paint-gate.ts's viewportHiddenSinceLoad over the page's window (feed-age.test.ts pins that feed.ts itself carries no probe)");
  assert.doesNotMatch(SRC, /window\.innerWidth === 0/, "no probe text in feed.ts: the standing gate never reads one (feed-age.test.ts), and the first-paint hold reads it through paint-gate.ts");
  assert.match(SRC, /if \(m\.romp === "panes"\) \{\n(?:\s*\/\/[^\n]*\n)*\s*if \(m\.on && typeof m\.on === "object"\) \{\n\s*feedShellOn = m\.on\.feed === true;\n\s*if \(feedShellOn && paintDirty && parentMobile\(\) === true\) \{ feedIntersecting = true; releasePaint\(\); \}\n\s*\}\n\s*return;\n\s*\}/,
    "the panes word: this pane's on-screen word, and on the phone's show the release of the owed paint (the word stands in for the observer's, the revealCard precedent)");
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
