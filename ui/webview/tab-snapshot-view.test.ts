// THE SECTION SNAPSHOT, VIEW HELPERS (tab-snapshot-view.ts; the round-2 review of the tabsnapshot branch):
// the pane-side rules render.ts applies to the snapshot, pure so they execute here without a DOM. The
// model and its words are tab-snapshot.ts; the render.ts pins are tab-snapshot-pane.test.ts. Synthetic
// only: the notes-api demo world (web / api / tests), placeholder ids.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { rowStillOpen, installSnapshotEscape } from "./tab-snapshot-view";

test("a row whose session left the strip mid-press opens nothing (round 2): a frame's row needs its session, a placeholder's row its meta, and a closing tab is neither", () => {
  // click safety keeps the pressed row in the DOM until the release, so a session dismissed between mousedown
  // and mouseup (the kernel's closed frame, a tabOrder push without it) is still under the click. setActive on
  // that id found tabMeta still holding it (dismissSession leaves tabMeta to the next tabOrder frame) and put
  // up an "opening…" loader, composer enabled, for a session that never arrives.
  const frame = { loading: false }, placeholder = { loading: true };
  assert.equal(rowStillOpen(frame, true, true, false), true, "a live row with its session: opens");
  assert.equal(rowStillOpen(frame, false, true, false), false, "its session gone, its meta lingering (closed frame before the next tabOrder push): nothing opens");
  assert.equal(rowStillOpen(frame, false, false, false), false, "session and meta gone (a tabOrder push without it): nothing opens");
  assert.equal(rowStillOpen(placeholder, false, true, false), true, "a placeholder row (no frame yet) with its meta: opens, the loading branch is its state");
  assert.equal(rowStillOpen(placeholder, false, false, false), false, "a placeholder whose meta left: nothing opens");
  assert.equal(rowStillOpen(placeholder, true, false, false), true, "a placeholder whose frame landed mid-press: the session is there, it opens");
  assert.equal(rowStillOpen(frame, true, true, true), false, "the user closed it (closingTabs): nothing opens, whatever the maps still hold");
  assert.equal(rowStillOpen(undefined, true, true, false), true, "no model row for the id (never expected): the session decides");
  assert.equal(rowStillOpen(undefined, false, true, false), false);
});

// ── the snapshot's Escape, two phases on one window ───────────────────────────────────────────────
// A stand-in for one keydown's dispatch through the chat frame, in DOM order: the window's capture listeners,
// the DOCUMENT's capture listeners (where the shell's Escape chain sits: kernel.py _LANDING_ESC_JS wires onEsc
// onto this frame's contentDocument at capture), then the target and the bubble back up to the window. A
// listener that stops propagation ends the walk, as in a browser.
type Fn = (e: KeyboardEvent) => void;
function frame() {
  const winCap: Fn[] = [], winBub: Fn[] = [], docCap: Fn[] = [];
  const win = { addEventListener: (_t: "keydown", fn: Fn, capture?: boolean) => { (capture ? winCap : winBub).push(fn); } };
  const dispatch = (e: KeyboardEvent) => {
    const ev = e as unknown as { stopped: boolean };
    for (const f of winCap) f(e); if (ev.stopped) return;
    for (const f of docCap) f(e); if (ev.stopped) return;
    for (const f of winBub) f(e);
  };
  return { win, docCap, winCap, winBub, dispatch };
}
const key = (k: string, target: EventTarget | null = null) => {
  const e = { key: k, target, defaultPrevented: false, stopped: false,
    preventDefault() { this.defaultPrevented = true; }, stopPropagation() { this.stopped = true; } };
  return e as unknown as KeyboardEvent;
};
// the shell's chain, as _LANDING_ESC_JS behaves: a panel open → close it, mark the Escape, stop it; else nothing
const shell = (panel: { open: boolean }) => (e: KeyboardEvent) => { if (e.key === "Escape" && panel.open) { panel.open = false; e.preventDefault(); e.stopPropagation(); } };

test("Escape leaves the snapshot only when no layer claimed it: the shell's panels (log, usage, network) live out of this page's sight, so the decision waits for the shell's chain (round 2)", () => {
  // the one-phase handler (window capture) ran before the shell's document-capture chain and could not see the
  // shell document's panels: an Escape aimed at the log panel closed it AND swapped the pane. Two phases now:
  // armed at capture (this page's own layers still on the page to be seen), decided at bubble, which an Escape the
  // shell stopped never reaches
  const f = frame();
  const panel = { open: true };
  f.docCap.push(shell(panel));
  let showing = true, left = 0, layer = false;
  installSnapshotEscape(f.win, { showing: () => showing, typing: () => false, layerOpen: () => layer, leave: () => { left++; showing = false; } });
  assert.equal(f.winCap.length, 1); assert.equal(f.winBub.length, 1, "one listener per phase");
  // 1. a shell panel open: the shell closes it and stops the Escape; the snapshot stays
  let e = key("Escape"); f.dispatch(e);
  assert.equal(panel.open, false, "the shell closed its panel");
  assert.equal(left, 0, "…and the snapshot stayed");
  assert.equal(e.defaultPrevented, true, "the shell's mark");
  // 2. nothing open anywhere: the Escape reaches the bubble unclaimed; the snapshot leaves, once, marked
  e = key("Escape"); f.dispatch(e);
  assert.equal(left, 1, "left"); assert.equal(e.defaultPrevented, true, "and marked as taken");
  f.dispatch(key("Escape"));
  assert.equal(left, 1, "not showing any more: nothing to leave");
});

test("the arm yields to this page's own layers at capture, to an earlier capture listener's mark, and to a typing target; a stale arm never fires on a later key", () => {
  const f = frame();
  let left = 0, layer = false, typing = false;
  installSnapshotEscape(f.win, { showing: () => true, typing: () => typing, layerOpen: () => layer, leave: () => { left++; } });
  layer = true; f.dispatch(key("Escape")); assert.equal(left, 0, "a page layer open at capture (a menu, the picker, a preview): not armed, even though nothing marks the Escape later");
  layer = false; typing = true; f.dispatch(key("Escape")); assert.equal(left, 0, "a field keeps its Escape");
  typing = false;
  // the tab menu's closer: a window-capture listener registered before this one, marking the Escape it consumed
  f.winCap.unshift((e) => { if (e.key === "Escape") e.preventDefault(); });
  f.dispatch(key("Escape")); assert.equal(left, 0, "an Escape already marked at capture is not ours");
  f.winCap.shift();
  // an Escape the shell stopped leaves the arm set; the next key must not inherit it
  const panel = { open: true }; f.docCap.push(shell(panel));
  f.dispatch(key("Escape")); assert.equal(left, 0, "stopped by the shell");
  f.docCap.pop();
  f.dispatch(key("a")); assert.equal(left, 0, "a later, unrelated key reaching the bubble does not fire the stale arm");
  f.dispatch(key("Escape")); assert.equal(left, 1, "the next unclaimed Escape does");
  // a mark set BETWEEN the phases by a listener that does not stop propagation (a target-phase handler) also wins
  f.docCap.push((e) => { if (e.key === "Escape") e.preventDefault(); });
  f.dispatch(key("Escape")); assert.equal(left, 1, "marked between the phases: yielded");
});
