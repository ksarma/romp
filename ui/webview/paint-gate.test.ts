// The shared paint gate (the user 2026-09-07, whose dashboard froze on the return to its browser tab):
// a pane applies every frame but paints only when it can be seen. Pure, so the truth table and the release
// ordering run executably; feed-hidden-paint.test.ts and outline-visibility.test.ts pin the wiring.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { paintHeld, paintReleased, publishPaneHidden, type PaneHiddenHost } from "./paint-gate";

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

test("the shim's word: the union of both measures, published as a boolean on the host; unset until the first event (the probe's turn)", () => {
  // The kernel's pane shim (kernel.py paneHidden) reads window.__rompPaneHidden when it is a boolean and falls back
  // to its zero-viewport probe otherwise. The probe is right for a pane hidden since load and wrong for one hidden
  // after a first show (the iframe keeps its size), so the gate, which sees both cases, publishes its word.
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
    assert.equal(typeof w.__rompPaneHidden, "boolean");
  }
});
