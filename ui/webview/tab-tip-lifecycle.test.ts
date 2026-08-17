// The tab hover tip must never outlive the hover that opened it (the user 2026-08-17: hover a tab, click a
// DIFFERENT tab → the tip sometimes stuck open showing the old tab's info, occluding the UI beneath it —
// z-index 70 over the meta menu's 60 — so clicks under it read as dead). The mechanism is the documented
// replaceChildren fact (timeline-rehover.test.ts): the tip's ONLY closer is the hovered tab's mouseleave,
// and renderTabs()'s `bar.replaceChildren()` destroys that tab on every push and on every setActive — a
// destroyed node fires no mouseleave, and the pointer never moved so the replacement gets no mouseenter.
// Orphaned open, no live closer. Two closers fix it: setActive closes the tip like the popovers it already
// closes, and renderTabs itself restores-or-closes a tip whose owner it just destroyed (the timeline's
// _rehover shape). Source pins over render.ts.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const RENDER = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "render.ts"), "utf8");

// ── piece 1: switching sessions closes the tip, like the meta menu and comment popover ──

test("setActive closes the tab tip in its existing close-the-leaving-tab's-popovers cluster", () => {
  // the cluster right after setActive's early return: closeMetaMenu / closeCommentPop / hideTabTip — the
  // SAME bug class as the comment popover (the user 2026-08-13: it lingered over the next tab's chat)
  const start = RENDER.indexOf("function setActive(");
  const fn = RENDER.slice(start, RENDER.indexOf("pendingAnchorT =", start));
  assert.match(fn, /closeMetaMenu\(\);/);
  assert.match(fn, /hideTabTip\(\);/, "switching sessions closes the hover tip");
});

// ── piece 2: renderTabs restores-or-closes the tip its own rebuild just orphaned ──
// This is the load-bearing invariant: renderTabs runs on every kernel push (0.5–3s), not just on clicks,
// so the click-path closer above cannot be the only guard.

test("the open tip records its owner tab node, and hiding clears it", () => {
  assert.match(RENDER, /let tabTipOwner: HTMLElement \| null = null;/);
  // recorded as the tip is actually SHOWN (after the empty-content bail), so owner != null ⇔ tip open
  assert.match(RENDER, /tabTipOwner = tab;[^\n]*\n\s*tip\.style\.display = "block";/);
  assert.match(RENDER, /function hideTabTip\(\): void \{ if \(tabTipEl\) tabTipEl\.style\.display = "none"; tabTipOwner = null; \}/);
});

test("renderTabs, after its rebuild, restores-or-closes a tip whose owner it destroyed", () => {
  // beside the refocusTab restore — the same carried-across-replaceChildren shape
  assert.match(RENDER,
    /if \(refocusTab\) focusActiveTab\(\);\n[\s\S]{0,400}?if \(tabTipOwner && !tabTipOwner\.isConnected\) rehoverTabTip\(\);/,
    "the staleness check runs right after the rebuild, next to the focus restore");
});

test("rehoverTabTip hit-tests the tracked pointer: a session tab there → re-show for THAT tab, else close — no timer", () => {
  const start = RENDER.indexOf("function rehoverTabTip()");
  assert.ok(start > 0, "rehoverTabTip exists");
  const fn = RENDER.slice(start, RENDER.indexOf("\n}", start) + 2);
  assert.match(fn, /document\.elementFromPoint\(p\.x, p\.y\)/, "hit-test where the pointer already is");
  assert.match(fn, /closest\("#tabs \.tab"\)/, "resolve to a tab of THIS strip");
  assert.match(fn, /if \(tab && s\) showTabTip\(tab, s\);\n\s*else hideTabTip\(\);/, "re-show fresh for the tab under the pointer, or close");
  assert.doesNotMatch(fn, /setTimeout|setInterval/, "event-based: keyed on the rebuild, never a timer or grace period");
});

test("the strip tracks the pointer for the re-hover, cleared on leave (the timeline's _ptr)", () => {
  assert.match(RENDER, /let tabsPtr: \{ x: number; y: number \} \| null = null;/);
  assert.match(RENDER, /tabs\.addEventListener\("pointermove", \(e\) => \{ tabsPtr = \{ x: e\.clientX, y: e\.clientY \}; \}\);/);
  assert.match(RENDER, /tabs\.addEventListener\("pointerleave", \(\) => \{ tabsPtr = null; \}\);/);
});

// ── executed replica of rehoverTabTip's decision (verbatim control flow) ──
type TabNode = { dataset: { id?: string } };

function rehoverReplica(
  p: { x: number; y: number } | null,
  elementFromPoint: (x: number, y: number) => { closest: (sel: string) => TabNode | null } | null,
  sessions: Map<string, unknown>,
): { action: "show"; tab: TabNode } | { action: "hide" } {
  const hit = p ? elementFromPoint(p.x, p.y) : null;
  const tab = hit ? hit.closest("#tabs .tab") : null;
  const s = tab?.dataset.id ? sessions.get(tab.dataset.id) : null;
  if (tab && s) return { action: "show", tab };
  return { action: "hide" };
}

test("executed: a stationary cursor over the rebuilt strip gets the tip back, for the tab NOW under it", () => {
  const sessions = new Map([["s-web", { name: "web" }]]);
  const tab: TabNode = { dataset: { id: "s-web" } };
  const r = rehoverReplica({ x: 40, y: 12 }, () => ({ closest: () => tab }), sessions);
  assert.deepEqual(r, { action: "show", tab }, "fresh showTabTip for the hit tab — also un-stales content held open across pushes");
});

test("executed: a cursor that left the strip closes the orphaned tip instead of resurrecting it", () => {
  const r = rehoverReplica(null, () => { throw new Error("must not hit-test without a position"); }, new Map());
  assert.deepEqual(r, { action: "hide" });
});

test("executed: the add-tab '+' (no session id) closes the tip rather than showing an empty one", () => {
  const add: TabNode = { dataset: {} };
  const r = rehoverReplica({ x: 5, y: 5 }, () => ({ closest: () => add }), new Map([["s-web", {}]]));
  assert.deepEqual(r, { action: "hide" });
});

test("executed: a placeholder tab (id pushed, session not yet landed) closes the tip", () => {
  const ph: TabNode = { dataset: { id: "s-api" } };
  const r = rehoverReplica({ x: 5, y: 5 }, () => ({ closest: () => ph }), new Map([["s-web", {}]]));
  assert.deepEqual(r, { action: "hide" });
});

test("executed: nothing under the pointer (strip shrank) closes the tip", () => {
  const r = rehoverReplica({ x: 900, y: 12 }, () => null, new Map([["s-web", {}]]));
  assert.deepEqual(r, { action: "hide" });
});
