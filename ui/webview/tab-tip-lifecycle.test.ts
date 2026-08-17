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
