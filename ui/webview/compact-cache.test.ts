// Compact-mode transcript caching (the user 2026-06-17, generalized 2026-06-25): a tab switch must NOT
// re-tear-down the whole transcript. Compact now shares the SINGLE virtualization path with normal mode —
// syncView's no-op fast path reveals the cached DOM unless the event set changed (append/rewind), the view
// was updated while hidden (stale), or a tool-group was toggled (which sets stale → re-render the current
// window). Source-level pin (no jsdom for the chat renderer).
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const RENDER = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "render.ts"), "utf8");

test("a switch with no change is a NO-OP (the cached DOM is revealed), in compact too", () => {
  assert.match(RENDER, /if \(v\.rendered === len && !v\.stale && v\.el\.childNodes\.length > 0\) return v;/);
});

test("compact mode paints its tail by unit first (PR E), and a stale view or a plan the trim cannot serve re-renders the CURRENT window (not a full transcript rebuild)", () => {
  // the incremental seam (chat-compact-tail.test.ts drives the plan and the trim) sits ahead of the rebuild, which stays the fallback
  const sync = RENDER.slice(RENDER.indexOf("function syncViewInner("), RENDER.indexOf("function patchWorkedFooters("));
  const seam = sync.indexOf("if (settings.compact) {\n    const plan = compactTailPlan(");
  const rebuild = sync.indexOf("if (settings.compact || v.stale) {");
  assert.ok(seam > 0 && rebuild > seam, "the plan runs before the rebuild");
  assert.match(sync, /if \(settings\.compact \|\| v\.stale\) \{[\s\S]*?renderWindowItems\(v, s, items, ws, we, working, anchored\); v\.stale = false; return v;/);
  assert.match(sync, /if \(plan\.kind === "append"\) \{[\s\S]*?trimUnitsFrom\(v\.el, u0\);/, "an append trims by unit instead of clearing the window");
});

test("toggling a tool group forces a re-render past the cache (sets stale) — an expand still repaints", () => {
  // the view is read before the sync since review round 1 (the toggle captures the reader's anchor on it first: toolgroup-toggle-keep.test.ts)
  assert.match(RENDER, /const v = activeId \? views\.get\(activeId\) : undefined;[\s\S]*?if \(activeId\) \{ if \(v\) v\.stale = true; syncView\(activeId, undefined, true\); \}/);   // anchored: the toggle's keep restores the anchor row after the build (review round 1b)
});
