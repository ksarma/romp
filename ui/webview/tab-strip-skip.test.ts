// renderTabs skips an unchanged strip (2026-09-06). It runs on every kernel push; on a 33-tab dashboard most
// tails go to tabs that are not active, and rebuilding every tab node with its listeners and then reading each
// one's offsetTop (paintTabRowLines forces a layout) was those tails' whole 2-4 ms floor. The strip now
// computes a signature of every input it paints and returns before the rebuild when it equals the last one.
// No DOM harness executes render.ts (the other render tests say so), so the rule is pinned at the source:
// the signature sits before the wipe, it names each input the strip renders, and the one place that mutates
// the strip's DOM outside renderTabs — a drag — resets it. The correctness of a signature skip rests on the
// input list being complete; this test is the list, so a new input the strip renders has to land here too.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const RENDER = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "render.ts"), "utf8");
const fn = RENDER.slice(RENDER.indexOf("function renderTabs() {"), RENDER.indexOf("function stripAftermath("));
const sig = fn.slice(fn.indexOf("const stripSig = JSON.stringify(["), fn.indexOf("const mslotEl = "));

test("the signature is computed before the wipe, and an equal one returns before any node is built", () => {
  assert.ok(fn.indexOf("const stripSig = JSON.stringify([") < fn.indexOf("bar.replaceChildren();"), "signature before the wipe");
  assert.match(fn, /if \(stripSig === tabStripSig && !\(mslotEl && !mslotEl\.firstChild\)\) \{ stripAftermath\(visibleIds, ids\); return; \}\s*\n\s*tabStripSig = stripSig;/,
    "an equal signature keeps the DOM; the mobile slot's once-only mount still happens; the aftermath still reconciles");
  // the guards that already stood keep standing, ahead of the signature
  assert.ok(fn.indexOf("if (renameActive)") < fn.indexOf("const stripSig") && fn.indexOf("if (tabPointerHeld)") < fn.indexOf("const stripSig"));
  // the focus capture + wipe keep their shape, now after the check (chat-focus-model / tab-group-flags pin the pair)
  assert.match(fn, /const refocusTab = bar\.contains\(document\.activeElement\);\s*\n\s*bar\.replaceChildren\(\);/);
});

test("every input the strip renders is in the signature", () => {
  for (const needle of [
    "activeId", "peekId", "phoneLayout()", "plan.sectioned", "ids", "visibleIds", "tabInView(activeId)",
    "settings.tabCtx", 'titleWithKey("Open a session", "session.new")',
    'surfaceLens(effViews(), "chat")', "viewTagUnion(effViews())",
    "it.head.name", "it.head.localId", "it.head.color", "it.head.ids", "it.folded", "it.active", "it.hidden",
    "snapView",   // the section whose snapshot the pane shows: a header's snap-shown mark and its way-back act derive from it (makeGroupHead), and leaveSnapshot changes it with no fold change
    "m?.name", "m?.color?.bg", "m?.color?.fg", "m?.emoji",
    "s.name", "s.color?.bg", "s.color?.fg", "s.emoji ?? tabMeta.get(id)?.emoji", "st.state", "tabStateClass(st)", "!!st.faded",
    "st.ctx", "st.ctxColor", "st.ctxTone", "!!(s.userTodos && s.userTodos.length)", "hostIsDown(id)", "hostDownNote(id)",
  ]) assert.ok(sig.includes(needle), "the signature reads " + needle);
  // per VISIBLE id, not per rendered tab: a folded header's pip and flag derive from its hidden members
  assert.match(sig, /visibleIds\.map\(\(id\) => \{/);
});

test("a drag resets the signature (its live reorder changes the strip's DOM outside renderTabs), and the tooltip reads the session fresh", () => {
  assert.match(fn, /tab\.addEventListener\("dragstart", \(e\) => \{\s*\n\s*draggedId = id; tabDragCommitted = false;\s*\n\s*tabStripSig = "";/);
  assert.match(fn, /showTabTip\(tab, sessions\.get\(id\) \?\? s\)/, "a tab node now outlives a frame that replaced the session object");
  assert.match(RENDER, /^let tabStripSig = "";/m);
});

test("what follows a render runs on both paths: the placeholder, the section snapshot's refresh and the all-hidden blank", () => {
  assert.match(RENDER, /function stripAftermath\(visibleIds: readonly string\[\], ids: readonly string\[\]\): void \{\s*\n\s*syncNoSessionsPlaceholder\(visibleIds\.length, ids\.length\);/);
  assert.equal((fn.match(/stripAftermath\(visibleIds, ids\)/g) || []).length, 2, "the skip path and the rebuild path");
  // the snapshot's rows read a member's last event and working note, which the strip's signature does not carry:
  // a push that leaves the strip as it was still refreshes them (tab-snapshot-pane pins the block's shape)
  const after = RENDER.slice(RENDER.indexOf("function stripAftermath("), RENDER.indexOf("function dismissTabMenu() {"));
  assert.match(after, /if \(snapView\) renderSnapshot\(\);/, "the snapshot refresh is in the aftermath, not behind the skip");
  assert.ok(!fn.includes("renderSnapshot("), "renderTabs itself does not call it: only the aftermath, which both paths reach");
  // …and the plan it reads is set before the skip returns
  assert.ok(fn.indexOf("lastStripItems = plan.items;") < fn.indexOf("const stripSig"), "lastStripItems is updated ahead of the skip");
});
