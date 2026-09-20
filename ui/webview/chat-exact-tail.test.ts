// The chat's tail path re-renders exactly what changed. The kernel's chatTail names the first changed event;
// the client used to re-render from min(that, len - 25) "in case an earlier event mutated in place" — a
// trailing window that was most of a tail's render and stood in for two signals the client can give itself:
// a reconcile pass that touched a prefix event (the editable set, the rewind dim) marks the view stale, and a
// full session frame for a held session rebuilds the window. The one render that depends on later events, the
// "worked …" footer, is patched by unit (worked-footer.ts, its own executed tests). chatTail and
// patchWorkedFooters are lifted and RUN by chat-exact-tail-exec.test.ts (review find, 2026-09-08); the pins
// here cover what no harness lifts: syncViewInner's wiring, reconcileRewind's delegation, the frame paths.
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

test("reconcileRewind delegates to the pure pass and marks the view stale on its signal, on every path", () => {
  // the pass and the stale signal are rewind-reconcile.ts, executed by rewind-reconcile.test.ts (a compaction at
  // `from`, a TTL expiry on a full or partial tail, a plain prompt append); render.ts keeps the session's set,
  // the pending entry and the view mark
  const fn = RENDER.slice(RENDER.indexOf("function reconcileRewind("), RENDER.indexOf("// Tab name+color from the kernel's tabOrder push"));
  assert.match(fn, /const r = reconcileRewindPass\(s\.events as RewindEvent\[\], \(s as any\)\._editable, pendingRewind\.get\(s\.id\),\s*\n\s*\{ sdk: s\.status\?\.backend === "sdk", now: Date\.now\(\), ttlMs: REWIND_TTL_MS, optPrefix: OPT_PREFIX, bound \}\);/);
  assert.match(fn, /\(s as any\)\._editable = r\.editable;/);
  assert.match(fn, /if \(!r\.pending\) pendingRewind\.delete\(s\.id\);/);
  assert.match(fn, /if \(v && r\.stale\) v\.stale = true;/);
  assert.doesNotMatch(fn, /\n\s*return;\s*\n/, "no early return skips the mark");
  assert.doesNotMatch(RENDER, /function rewindSig\(/, "one signature, in the module");
});

test("a full frame for a held session and a wholesale events replacement rebuild the window (the tail path trusts v.rendered)", () => {
  const up = RENDER.slice(RENDER.indexOf("function upsert(msg: any) {"), RENDER.indexOf("function update(msg: any) {"));
  // `!kept`: a frame that carried no events for a session with content keeps the resident events (T249b,
  // frame-merge.ts) — nothing was replaced, so a status-shaped frame leaves the view as it is
  assert.match(up, /\} else if \(existed && !kept\) \{[\s\S]{0,900}?const v = views\.get\(msg\.id\);\s*\n\s*if \(v\) v\.stale = true;\s*\n\s*\}/);
  assert.ok(up.indexOf("const kept = keepResidentEvents(") < up.indexOf("} else if (existed && !kept) {"), "the keep decision precedes the stale mark");
  const upd = RENDER.slice(RENDER.indexOf("function update(msg: any) {"), RENDER.indexOf("function update(msg: any) {") + 1200);
  assert.match(upd, /if \(msg\.events\) \{ const v0 = views\.get\(msg\.id\); if \(v0\) v0\.stale = true; \}/);
});

test("the render and the footer patch share one elapsed rule", () => {
  // the patch itself (add, remove, the fork spot's re-homing, the day-divider skip, compact-mode units) runs in
  // chat-exact-tail-exec.test.ts; this pins that the render's per-turn footer reads the same module rule
  assert.match(RENDER, /function turnWorkedSecs\(events: ChatEvent\[\], i: number, working: boolean\): number \| null \{\s*\n\s*return workedSecsOf\(events, i, working, eventEpoch\);/, "one rule for the render and the patch");
  const fn = RENDER.slice(RENDER.indexOf("function patchWorkedFooters("), RENDER.indexOf("function patchWorkedFooters(") + 1500);
  assert.match(fn, /workedFooterPlan\(s\.events, from, winEv, working, eventEpoch\)/, "the patch takes its plan from the module");
});

test("a status-only tail reaches the footer: the view remembers the working state, and a flip patches from the fast path with from = len", () => {
  // chatTail with an empty suffix leaves v.rendered === len, so syncViewInner's no-op fast path is the only
  // code that runs for it; the footer's one non-event input is the session's working state
  assert.match(RENDER, /^interface View \{[^\n]*working\?: boolean;/m);
  const sync = RENDER.slice(RENDER.indexOf("function syncViewInner("), RENDER.indexOf("function patchWorkedFooters("));
  assert.match(sync, /const workFlip = v\.working != null && v\.working !== working;\s*\n\s*v\.working = working;/);
  assert.match(sync, /if \(workFlip && v\.rendered === len && !v\.stale && v\.el\.childNodes\.length > 0\) \{\s*\n\s*patchWorkedFooters\(v, s, len, working, settings\.compact \? items : null\);\s*\n\s*\}\s*\n\s*if \(v\.rendered === len && !v\.stale && v\.el\.childNodes\.length > 0\) return v;/,
    "the flip patches just ahead of the fast path under its predicate, and the fast path (its line pinned by other tests) still returns; a patch that could not address the unit marks stale, so the window path re-renders");
});

test("a plain human-prompt append does not set stale: the signature reads the prefix below the tail's re-render start", () => {
  // a landing prompt is a new editable bubble, so an unbounded editable set differed on every prompt and
  // rebuilt the whole window; the tail renders everything at or past `from` itself (executed:
  // rewind-reconcile.test.ts; here, that chatTail hands its `from` over as the bound)
  assert.match(RENDER, /function reconcileRewind\(s: Session, bound\?: number\): void \{/);
  // (that chatTail hands its `from` over as the bound, lowers v.rendered to it, and still rebuilds the window on a
  // shrunken tail or a change inside a scrolled-away window, runs in chat-exact-tail-exec.test.ts)
});

// ── the desktop's tail path under PR E (2026-09-19) ────────────────────────────────────────────────
// Compact mode's tail path by unit (chat-compact-tail.test.ts) was inserted ABOVE normal mode's block and the two fixes to the
// spacers' measurement live in functions of their own; the normal-mode block (from "Normal mode, pure append." to syncViewInner's
// closing brace) is recorded here line by line and pinned byte for byte, so a change to the desktop's path is a deliberate edit
// of this record, never a side effect. On a failure the diff says what moved. One deliberate edit so far (review round 2): the
// block's own copy of the tail walk, which stopped at a foreign child (a hover's rail band) and re-appended the tail on top of a
// stale copy of itself, gave way to trimUnitsFrom, the walk compact mode's seam uses (compact-seam-exec.test.ts executes the call;
// chat-compact-tail.test.ts drives the walk over a band).
const NORMAL_MODE_BLOCK = [
  "  // Normal mode, pure append. While BROWSING history (window not at the tail), the new events land below the",
  "  // rendered window → just grow the bottom spacer (no DOM churn); the user sees them on scroll-down.",
  "  if (!wasAtTail) {",
  "    v.spacerCountBot = total - (v.winEnd ?? total); v.unitTotal = total; v.rendered = len; sizeSpacers(v); return v;",
  "  }",
  "  // Normal mode, append AT the tail (unit === event, top spacer only): the cheap incremental hot path —",
  "  // re-render EXACTLY from the first changed event, tagging data-unit so the scroll↔unit map stays valid.",
  "  // v.rendered is exact: the kernel's chatTail names the first changed index (its _chat_diff compares by",
  "  // identity first, then equality, and the fold never writes an event in place), and every client pass that",
  "  // touches a prefix event marks the view stale instead — reconcileRewind (the editable set, the rewind dim),",
  "  // reconcileOptimistic (the echo set), a full session frame (upsert) — which takes the window rebuild above.",
  "  // A trailing window of 25 events re-rendered on every tail used to stand in for those signals, and was",
  "  // most of a tail's render. The one render that depends on LATER events, the \"worked …\" footer of a turn's",
  "  // last reply, is patched by unit after the loop (patchWorkedFooters).",
  "  const from = Math.max(v.rendered, v.winStart ?? 0);",
  "  // Drop every node from unit `from` onward, then re-render that span. Trim by DATA-UNIT, never by",
  "  // child COUNT: a unit can put more than one node in the thread (a day divider precedes the turn",
  "  // that opens a new day), so `keep = spacer + (from - winStart)` counted one node per unit and the",
  "  // extra dividers made it delete that many live turns off the tail, which then never came back.",
  "  // Reading the unit off the node is exact however many nodes a unit owns; the top spacer carries no",
  "  // data-unit, so it ends the walk, and a foreign child met on the way (a hover's rail band) is dropped:",
  "  // trimUnitsFrom, the one walk both tail paths share (review round 2; this mode's own copy stopped at",
  "  // the band and re-appended the tail on top of a stale copy of itself, one stranded duplicate per hover).",
  "  trimUnitsFrom(v.el, from);",
  "  const walk = dayWalkBeforeEvent(s.events, from);   // the day walk's high-water mark up to here (T339)",
  "  for (let i = from; i < len; i++) {",
  "    const prev = prevTimedEpoch(s.events, i);   // the rail's raw previous epoch (the same-minute rule)",
  "    const ep = eventEpoch(s.events[i]);",
  "    if (ep != null) {   // a day boundary opens with its divider here too, or the tail append would drop it",
  "      const dv = dayDividerFor(ep, walk);",
  "      if (dv) { dv.dataset.unit = String(i); v.el.appendChild(dv); }",
  "    }",
  "    const node = renderEvent(s.events[i], prev, turnWorkedSecs(s.events, i, working));",
  "    node.dataset.unit = String(i);   // unit === event in normal mode",
  "    v.el.appendChild(node);",
  "    walk.pass(ep);",
  "    stampWalkDay(node, walk);",
  "  }",
  "  patchWorkedFooters(v, s, from, working);",
  "  v.winEnd = total; v.spacerCount = v.winStart ?? 0; v.spacerCountBot = 0; v.unitTotal = total; v.rendered = len;",
  "  return v;",
  "}"
].join("\n") + "\n";

test("normal mode's tail block is byte-identical to the recorded text, sits after compact mode's seam and the rebuild, and reads none of the compact seam's plan, eviction or measurement helpers (the trim is the one walk both paths share)", () => {
  const sync = RENDER.slice(RENDER.indexOf("function syncViewInner("), RENDER.indexOf("function patchWorkedFooters("));
  const at = sync.indexOf("  // Normal mode, pure append.");
  assert.ok(at > 0, "the block's opening comment");
  assert.equal(sync.slice(at, at + NORMAL_MODE_BLOCK.length), NORMAL_MODE_BLOCK, "normal mode's tail path changed; if that is deliberate, re-record the block here");
  assert.ok(sync.slice(at + NORMAL_MODE_BLOCK.length).trimStart().startsWith("//"), "the block closes syncViewInner: only the next function's comment follows it");
  const seamAt = sync.indexOf("if (settings.compact) {\n    const plan = compactTailPlan("), rebuildAt = sync.indexOf("if (settings.compact || v.stale) {");
  assert.ok(seamAt > 0 && seamAt < rebuildAt && rebuildAt < at, "the compact seam, then the rebuild, then normal mode");
  // trimUnitsFrom is not in this list since review round 2: the trim is unitOfNode's walk, the one predicate for what a view's child is,
  // and normal mode's own copy of it stopped at a foreign child (the block's one deliberate edit)
  assert.doesNotMatch(NORMAL_MODE_BLOCK, /compactTailPlan|evictCompactTop|reseedWindowHead|v\.units|measureDue|applyMeasure/, "no compact plan, eviction or measurement helper inside normal mode's block");
  assert.match(NORMAL_MODE_BLOCK, /\n  trimUnitsFrom\(v\.el, from\);\n/, "normal mode trims through the shared walk, from the first changed event");
  assert.ok(NORMAL_MODE_BLOCK.split("\n").length > 30, "the record holds the whole block, not a stub");
});
