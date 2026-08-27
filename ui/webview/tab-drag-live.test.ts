// Tab drag is LIVE REORDER (T127, the user 2026-08-27): while a tab drags, the other tabs
// rearrange in real time to make room, the way browser tab strips do — the old two-px landing
// marker is gone. The deciding event is the pointer crossing the MIDPOINT of the tab under it
// (never a timer); the dragged tab's in-flow element moves through the strip's DOM, the wrap
// layout reflows rows natively (true cross-row reorder: a tab pushed past a row's end wraps
// mid-drag), and siblings FLIP to their new rects. Verified end-to-end headless (synthetic drag
// events over the built bundle): same-row displacement, cross-row reflow, a push deferred across
// the whole drag, drop persistence surviving a forced re-render, and cancel animating home.
// Source pins per the repo convention (render.ts builds the strip imperatively; no jsdom here).
import { test } from "node:test";
import assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const RENDER = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "render.ts"), "utf8");
const CSS = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "styles.css"), "utf8");

const between = (a: string, b: string) => {
  const at = RENDER.indexOf(a);
  assert.ok(at > 0, a + " must exist");
  return RENDER.slice(at, RENDER.indexOf(b, at));
};

test("slot boundary is the event: midpoint compare moves the dragged element in DOM order", () => {
  const body = between('tabs.addEventListener("dragover"', "});");
  assert.match(body, /const ref = e\.clientX > r\.left \+ r\.width \/ 2 \? over\.nextElementSibling : over;/,
    "crossing the midpoint of the tab under the pointer decides the slot — an event, not a timer");
  assert.match(body, /if \(ref !== dragged && dragged\.nextElementSibling !== ref\) flipTabs\(\(\) => tabs\.insertBefore\(dragged, ref\)\);/,
    "already-in-place is a no-op, so a pointer resting in one slot never churns the DOM");
  assert.doesNotMatch(body, /setTimeout|debounce|Date\.now/, "no time-based logic in the reorder decision");
});

test("cross-row reflow is the wrap layout's own: DOM insertion, no per-row special case", () => {
  // the strip wraps (flex-wrap) — moving the element IS the cross-row mechanism, so there must be
  // no row math in the drag path
  assert.match(CSS, /#tabs \{ display: flex; flex: 1 1 auto; flex-wrap: wrap; align-items: stretch; gap: 0; \}/);
  const body = between('tabs.addEventListener("dragover"', "});");
  assert.doesNotMatch(body, /row|clientY/i, "no row bookkeeping — insertion order + wrap does it");
});

test("drop commits through the SAME reorderTo — neighbor + side, hidden-view ids keep their places", () => {
  const body = between('tabs.addEventListener("drop"', "});");
  assert.match(body, /if \(prev\?\.dataset\?\.id\) reorderTo\(draggedId, prev\.dataset\.id, true\);/);
  assert.match(body, /else if \(next\?\.dataset\?\.id\) reorderTo\(draggedId, next\.dataset\.id, false\);/);
  // …and reorderTo still persists exactly as before
  const rt = between("function reorderTo(", "\n}");
  assert.match(rt, /commitTabOrder\(\);/);
  assert.match(rt, /renderTabs\(\);/);
});

test("the drag covers the whole gesture against pushes, and dragend releases the hold by hand", () => {
  // pointerdown latches the hold BEFORE dragstart can fire; the drag swallows the pointerup, so
  // dragend clears it and flushes anything a push deferred mid-drag
  assert.match(RENDER, /tabs\.addEventListener\("pointerdown", \(\) => \{ tabPointerHeld = true; \}\);/);
  const de = between('tab.addEventListener("dragend"', "});");
  assert.match(de, /tabPointerHeld = false;/);
  assert.match(de, /const pending = renderPendingWhilePressed;/);
  assert.match(de, /else if \(pending\) setTimeout\(\(\) => renderTabs\(\), 0\);/);
});

test("cancel (Escape / dropped outside) re-renders from the untouched order, FLIP-animated home", () => {
  const de = between('tab.addEventListener("dragend"', "});");
  assert.match(de, /const cancelled = !tabDragCommitted;/);
  assert.match(de, /if \(cancelled\) flipTabs\(\(\) => renderTabs\(\)\);/);
  // the drop handler is what marks a commit, and it does so AFTER committing
  const drop = between('tabs.addEventListener("drop"', "});");
  assert.match(drop, /tabDragCommitted = true;/);
});

test("reduced motion: the mutation still happens, only the transition is skipped", () => {
  const flip = between("function flipTabs(", "\n}");
  assert.match(flip, /mutate\(\);\s*\n\s*if \(matchMedia\("\(prefers-reduced-motion: reduce\)"\)\.matches\) return;/,
    "the guard sits AFTER the mutation — positions always update; the reorder IS the information");
  assert.match(flip, /transform 0\.12s ease/, "duration is presentation, not logic — nothing waits on it");
});

test("the old landing marker is fully retired", () => {
  for (const [name, src] of [["render.ts", RENDER], ["styles.css", CSS]] as const) {
    assert.ok(!/drop-(?:before|after)/.test(src), name + " carries no landing-marker classes");
  }
});
