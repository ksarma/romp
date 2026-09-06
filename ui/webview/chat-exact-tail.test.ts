// The chat's tail path re-renders exactly what changed (2026-09-06). The kernel's chatTail names the first
// changed event; the client used to re-render from min(that, len - 25) "in case an earlier event mutated in
// place" — a trailing window that was most of a tail's render and stood in for two signals the client can
// give itself: a reconcile pass that touched a prefix event (the editable set, the rewind dim) marks the view
// stale, and a full session frame for a held session rebuilds the window. The one render that depends on later
// events, the "worked …" footer, is patched by unit (worked-footer.ts, its own executed tests). Source pins:
// no harness executes render.ts.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const RENDER = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "render.ts"), "utf8");

test("the tail path starts at the exact first changed event; the trailing re-check window is gone", () => {
  assert.doesNotMatch(RENDER, /const TAIL_RECHECK = \d+;/);
  assert.doesNotMatch(RENDER, /len - TAIL_RECHECK/);
  const sync = RENDER.slice(RENDER.indexOf("function syncViewInner("), RENDER.indexOf("function patchWorkedFooters("));
  assert.match(sync, /const from = Math\.max\(v\.rendered, v\.winStart \?\? 0\);/);
  assert.match(sync, /patchWorkedFooters\(v, s, from, working\);\s*\n\s*v\.winEnd = total;/, "the footers are reconciled after the exact re-render, before the bookkeeping");
});

test("reconcileRewind marks the view stale when the editable set or the overlay CHANGED — including the early-out paths", () => {
  const fn = RENDER.slice(RENDER.indexOf("function reconcileRewind("), RENDER.indexOf("function rewindSig("));
  assert.match(fn, /const before = rewindSig\(s\);/);
  assert.match(fn, /if \(v && rewindSig\(s\) !== before\) v\.stale = true;/);
  assert.doesNotMatch(fn, /\n\s*return;\s*\n/, "no early return skips the comparison: the landed/expired path and the no-pending path both reach it");
  const sigFn = RENDER.slice(RENDER.indexOf("function rewindSig("), RENDER.indexOf("function rewindSig(") + 700);
  for (const part of ["_editable", "rewound", "pendingRewind.get(s.id)", "pr.bare"]) assert.ok(sigFn.includes(part), "the signature covers " + part);
});

test("a full frame for a held session and a wholesale events replacement rebuild the window (the tail path trusts v.rendered)", () => {
  const up = RENDER.slice(RENDER.indexOf("function upsert(msg: any) {"), RENDER.indexOf("function update(msg: any) {"));
  assert.match(up, /\} else if \(existed\) \{[\s\S]{0,700}?const v = views\.get\(msg\.id\);\s*\n\s*if \(v\) v\.stale = true;\s*\n\s*\}/);
  const upd = RENDER.slice(RENDER.indexOf("function update(msg: any) {"), RENDER.indexOf("function update(msg: any) {") + 1200);
  assert.match(upd, /if \(msg\.events\) \{ const v0 = views\.get\(msg\.id\); if \(v0\) v0\.stale = true; \}/);
});

test("the footer patch adds, removes and re-homes the fork spot with the elapsed row, by unit and never a divider", () => {
  const fn = RENDER.slice(RENDER.indexOf("function patchWorkedFooters("), RENDER.indexOf("function patchWorkedFooters(") + 1500);
  assert.match(fn, /workedFooterPlan\(s\.events, from, v\.winStart \?\? 0, working, eventEpoch\)/);
  assert.match(fn, /:scope > \[data-unit="\$\{unit\}"\]:not\(\.day-divider\)/, "a day divider shares its turn's unit number");
  assert.match(fn, /if \(secs != null && !have\) \{[\s\S]*?node\.appendChild\(f\);\s*\n\s*if \(spot\) f\.appendChild\(spot\);/, "the fork spot moves into the new elapsed row, where applyForkSpots places it");
  assert.match(fn, /\} else if \(secs == null && have\) \{[\s\S]*?if \(spot\) node\.appendChild\(spot\);\s*\n\s*have\.remove\(\);/, "…and back onto the turn when the footer comes off");
  assert.match(RENDER, /function turnWorkedSecs\(events: ChatEvent\[\], i: number, working: boolean\): number \| null \{\s*\n\s*return workedSecsOf\(events, i, working, eventEpoch\);/, "one rule for the render and the patch");
});
