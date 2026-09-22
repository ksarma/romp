// The shared paint gate (the user 2026-09-07, whose dashboard froze on the return to its browser tab):
// a pane applies every frame but paints only when it can be seen. Pure, so the truth table and the release
// ordering run executably; feed-hidden-paint.test.ts and outline-visibility.test.ts pin the wiring.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { paintHeld, paintReleased, publishPaneHidden, firstPaintHeld, viewportHiddenSinceLoad, revealDecision, type PaneHiddenHost } from "./paint-gate";
import { hideEdges } from "../test-dom-shim";   // the fake-DOM rule (ui/test-dom-shim.test.ts): a window stand-in with a parent edge enumerates its primitives alone

test("the first content always paints through, whatever the visibility (the pane loader retires on it)", () => {
  assert.equal(paintHeld(true, true, false), false, "hidden tab, empty list");
  assert.equal(paintHeld(false, false, false), false, "display:none pane, empty list");
  assert.equal(paintHeld(true, false, false), false, "both");
});

test("with content on screen, EITHER measure holds the paint: a hidden tab, or a pane the observer cannot see", () => {
  assert.equal(paintHeld(false, true, true), false, "visible tab, intersecting pane → paint");
  assert.equal(paintHeld(true, true, true), true, "hidden tab with an on-screen pane — the case the observer-only gate missed");
  assert.equal(paintHeld(false, false, true), true, "display:none pane in a visible tab — the case document.hidden misses");
  assert.equal(paintHeld(true, false, true), true);
});

test("a release settles a paint only when one is owed AND both measures agree the pane can be seen", () => {
  assert.equal(paintReleased(false, false, true), false, "nothing owed → no paint (a visibilitychange with nothing pending)");
  assert.equal(paintReleased(true, false, true), true);
  assert.equal(paintReleased(true, true, true), false, "still hidden (an observer callback inside a hidden tab)");
  assert.equal(paintReleased(true, false, false), false, "tab back, pane still display:none → the observer's callback releases later");
});

test("release ordering: whichever measure clears LAST releases exactly once, in either order", () => {
  // tab hidden AND the pane display:none, a paint owed; the tab returns first, then the pane is shown
  let dirty = true;
  let paints = 0;
  const release = (docHidden: boolean, intersecting: boolean) => {
    if (!paintReleased(dirty, docHidden, intersecting)) return;
    dirty = false; paints++;
  };
  release(false, false);   // visibilitychange → visible, pane still hidden
  assert.equal(paints, 0);
  release(false, true);    // the observer: intersecting
  assert.equal(paints, 1);
  release(false, true);    // a second observer callback (a resize) — nothing owed any more
  assert.equal(paints, 1);
  // the other order: pane shown while the tab is hidden (a shell toggle from another script), then the tab returns
  dirty = true; paints = 0;
  release(true, true);
  assert.equal(paints, 0);
  release(false, true);
  assert.equal(paints, 1);
});

test("the pane's hidden word: the union of both measures, published as a boolean on the host, on the gate's own events", () => {
  // The kernel's pane shim gates its stale banner on paneHidden(), which reads its zero-viewport probe OR this word.
  // The probe is right for a pane hidden since load and, in Chromium, wrong for one hidden after a first show (the
  // iframe keeps its size), so the gate, which sees both cases, publishes what its two measures say.
  const w: PaneHiddenHost = {};
  assert.equal(typeof w.__rompPaneHidden, "undefined", "before the first event nothing is published: the shim's probe decides");
  assert.equal(publishPaneHidden(false, true, w), false, "visible tab, pane on screen");
  assert.equal(w.__rompPaneHidden, false);
  assert.equal(publishPaneHidden(false, false, w), true, "display:none pane in a visible tab: the re-hide the probe misses");
  assert.equal(w.__rompPaneHidden, true);
  assert.equal(publishPaneHidden(true, true, w), true, "hidden tab, pane on screen");
  assert.equal(publishPaneHidden(true, false, w), true, "both");
  assert.equal(publishPaneHidden(false, true, w), false, "shown again: the word follows the event, no timer");
  for (const [d, i] of [[false, true], [false, false], [true, true], [true, false]] as const) {
    assert.equal(publishPaneHidden(d, i, w), paintHeld(d, i, true), "the word is the gate's own hold decision with content present");
    assert.equal(typeof w.__rompPaneHidden, "boolean", "a boolean, the type the shim tests for");
  }
});

test("the observer's word is null until it speaks: the paint gate reads null as on screen, and the publisher publishes NOTHING for it", () => {
  // A page loaded in a background tab gets no IntersectionObserver callback until the tab's first rendering step
  // after its return, so the return's visibilitychange runs before the observer's first word. A word published then
  // would be document.hidden alone, which says visible for a display:none pane. So the word starts null: for the
  // paint that measure holds nothing (the first content painted through anyway), and the publisher stays silent, so
  // the probe decides at boot, on both arms of visibilitychange.
  assert.equal(paintHeld(false, null, true), false, "unspoken observer, visible tab: the paint proceeds, as with the old true default");
  assert.equal(paintHeld(true, null, true), true, "the tab's hiding still holds it");
  assert.equal(paintHeld(false, null, false), false);
  assert.equal(paintReleased(true, false, null), true, "a return with the observer unspoken releases the owed paint");
  assert.equal(paintReleased(true, true, null), false);
  const w: PaneHiddenHost = {};
  assert.equal(publishPaneHidden(false, null, w), null, "the visible arm before the observer's word: nothing");
  assert.equal(publishPaneHidden(true, null, w), null, "the hidden arm before it: nothing either (a page with no observer keeps the probe for good)");
  assert.equal(typeof w.__rompPaneHidden, "undefined", "unset: the shim's probe decides");
  assert.equal(publishPaneHidden(false, false, w), true, "the observer's first word publishes");
  assert.equal(publishPaneHidden(false, true, w), false);
  assert.equal(publishPaneHidden(true, true, w), true, "and the tab's arms publish once it has spoken");
});

test("the FIRST paint on the phone (stage 0, 2026-09-18): held while the pane is off screen, by the shell's word first, else the probe or the observer; never with content, never off the phone", () => {
  // off the phone nothing changes: the first content paints through as paintHeld lets it
  assert.equal(firstPaintHeld(false, undefined, false, true, false), false, "no shell probe (standalone, VS Code): the first paint goes through");
  assert.equal(firstPaintHeld(false, false, false, true, false), false, "the desktop grid: goes through");
  // on the phone, the shell's word when one has arrived
  assert.equal(firstPaintHeld(false, true, false, false, null), true, "the shell says the pane is off screen: held, whatever the probe and the observer say");
  assert.equal(firstPaintHeld(false, true, true, true, false), false, "the shell says on screen: paints, whatever the probe and the observer say (the word is the newer measure)");
  // no word yet: the shim's zero-viewport probe (a frame hidden since load) or the observer's word
  assert.equal(firstPaintHeld(false, true, undefined, true, null), true, "hidden since load, observer silent: held by the probe");
  assert.equal(firstPaintHeld(false, true, undefined, false, false), true, "a viewport, the observer says off screen: held");
  assert.equal(firstPaintHeld(false, true, undefined, false, null), false, "a viewport and no word from anyone: the pane is the shown tab, paint");
  assert.equal(firstPaintHeld(false, true, undefined, false, true), false, "the observer says on screen: paint");
  // with content the rule is paintHeld's alone
  assert.equal(firstPaintHeld(true, true, false, true, false), false, "a painted board is the standing gate's business");
});

test("the zero-viewport probe off a window: a framed pane at 0 by 0 has been hidden since load; a shown frame or a top-level page never reads hidden", () => {
  const framed = (w: number, h: number) => { const win: any = { innerWidth: w, innerHeight: h }; win.parent = {}; return hideEdges(win); };
  const top = (w: number, h: number) => { const win: any = { innerWidth: w, innerHeight: h }; win.parent = win; return hideEdges(win); };
  assert.equal(viewportHiddenSinceLoad(framed(0, 0)), true, "a framed pane never shown");
  assert.equal(viewportHiddenSinceLoad(framed(390, 0)), true, "either dimension");
  assert.equal(viewportHiddenSinceLoad(framed(390, 700)), false, "a shown frame has its size");
  assert.equal(viewportHiddenSinceLoad(top(0, 0)), false, "a top-level page is its own parent: the probe never applies");
});

test("a reveal's decision (review round 1 F2, executed since pass 2; the park's bound since pass 3): a found card is jumped to; a card the paint will stamp under an owed paint is parked while the pane is on screen or its place is unknown, dropped while the shell's word has it off screen, never opened; a card it will not stamp, or a gone one, opens its session when one is named", () => {
  // the columns: (targetFound, paintDirty, willPaint, hasSid, shellOn), shellOn the shell's last panes word for this pane (undefined before one)
  for (const on of [true, undefined, false] as const) {
    assert.equal(revealDecision(true, false, true, true, on), "jump", "the painted board has the card (shellOn " + on + ")");
    assert.equal(revealDecision(true, true, true, true, on), "jump", "found wins whatever else is true (shellOn " + on + ")");
    assert.equal(revealDecision(false, true, false, true, on), "open", "unpainted and the paint will NOT stamp it under this key (review round 2, 2026-09-19: a satellite, a filtered or lens-hidden card, a turn-group member, a gone card): open its session at the tap, the base's road, whatever the shell's word (shellOn " + on + ")");
    assert.equal(revealDecision(false, false, true, true, on), "open", "painted, not found, though the plan would stamp it (unfolded a beat late): the base's fallback (shellOn " + on + ")");
    assert.equal(revealDecision(false, false, false, true, on), "open", "gone from a painted board (shellOn " + on + ")");
    assert.equal(revealDecision(false, false, false, false, on), "none", "gone and no session named: nothing (shellOn " + on + ")");
    assert.equal(revealDecision(false, true, false, false, on), "none", "(shellOn " + on + ")");
  }
  // the park and its bound (review round 3, 2026-09-19, extra9-1): unpainted and the paint will stamp it
  assert.equal(revealDecision(false, true, true, true, true), "park", "the pane on screen by the shell's word with the browser tab hidden: the tab's return is this gesture's show");
  assert.equal(revealDecision(false, true, true, false, true), "park", "…with or without a session named");
  assert.equal(revealDecision(false, true, true, true, undefined), "park", "no word from the shell yet (the load-order race): the first word or show consumes it");
  assert.equal(revealDecision(false, true, true, false, undefined), "park");
  assert.equal(revealDecision(false, true, true, true, false), "drop", "the pane OFF screen by the shell's word and this gesture shows no tab (the phone's notification landing): no park for an unrelated later show, and no openSession either (the landing put the session in front): dropped, said by the caller");
  assert.equal(revealDecision(false, true, true, false, false), "drop", "…with or without a session named");
});
