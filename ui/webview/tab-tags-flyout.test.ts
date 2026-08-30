// The chat-tab context menu's Tags flyout opens on HOVER-INTENT and carries Configure tags…
// (T163, the user 2026-08-28: hovering down to Tags should open the submenu without another
// click, and it should have a thing that goes into the configure-tags dialog). Source pins; the
// hover/tolerance behavior is also driven headless over the built bundle (task harness).
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const RENDER = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "render.ts"), "utf8");
const at = RENDER.indexOf('const tagsItem = el("div", "ctx-item ctx-item-toggle ctx-item-tags");');
const block = RENDER.slice(at, RENDER.indexOf('menu.appendChild(tagsItem);', at));

test("hover-intent opens the flyout: the feed's 120ms, click still instant, hover never steals focus", () => {
  assert.match(block, /const HOVER_INTENT_MS = 120;/);
  assert.match(block, /tagsItem\.addEventListener\("pointerenter", \(\) => \{/);
  assert.match(block, /hoverOpenT = window\.setTimeout\(\(\) => \{ hoverOpenT = null; openTagsFly\(false\); \}, HOVER_INTENT_MS\);/,
    "hover opens WITHOUT focusing the input — a graze must not grab the keyboard");
  assert.match(block, /openTagsFly\(true\);/, "click opens instantly and focuses");
  assert.match(block, /cancelHoverTimers\(\);\s*\n\s*const openFly = menu\.querySelector\(".ctx-sub-tags"\);/,
    "a click cancels any pending hover intent before acting");
});

test("diagonal tolerance: entering either surface cancels the close; leaving both closes", () => {
  assert.match(block, /sub\.addEventListener\("pointerenter", cancelHoverTimers\);/);
  assert.match(block, /sub\.addEventListener\("pointerleave", armHoverClose\);/);
  assert.match(block, /tagsItem\.addEventListener\("pointerleave", armHoverClose\);/);
  assert.match(block, /hoverCloseT = window\.setTimeout\(/, "the close is armed on leave with the same tolerance window");
});

test("expansion follows the standing side rule and the caret faces right", () => {
  assert.match(block, /if \(ir\.right \+ 2 \+ sr\.width <= window\.innerWidth - 8\) sub\.style\.left = Math\.round\(ir\.right \+ 2\) \+ "px";/);
  assert.match(block, /else sub\.style\.left = Math\.max\(8, Math\.round\(ir\.left\) - sr\.width - 2\) \+ "px";/,
    "prefer right, FALL LEFT on clip — never slide over the row");
  assert.match(block, /caret\.textContent = "▸";/);
});

test("Configure tags… sits at the foot behind the divider and rides the ONE dialog route", () => {
  const cfgAt = block.indexOf('cfgL.textContent = "Configure tags…";');
  assert.ok(cfgAt > 0);
  assert.match(block, /sub\.appendChild\(el\("div", "ctx-sep"\)\);\s*\n\s*const cfg = el\("div", "ctx-item ctx-item-configtags"\);/);
  assert.match(block, /vscodeApi\?\.postMessage\(\{ type: "openTagsDialog" \}\);/,
    "the same route the tag-lens menus use — one dialog, no copy");
  assert.match(block, /e2\.stopPropagation\(\); dismissTabMenu\(\);/, "opening the dialog closes the menu");
});
