// renderTabs skips an unchanged strip. It runs on every kernel push; on a board of a few dozen tabs most
// tails go to tabs that are not active, and rebuilding every tab node with its listeners and then reading
// each one's offsetTop (paintTabRowLines forces a layout) was those tails' whole 2-4 ms floor. The strip
// now computes a signature of every input it paints and returns before the rebuild when it equals the last
// one. scheduleRenderTabs already coalesces the pushes of one animation frame into one call; the skip is
// the complement, for the frames whose call finds nothing changed.
// No DOM harness executes render.ts (the other render tests say so), so the rule is pinned at the source:
// the signature sits before the wipe, it names each input the strip renders — the strip PLAN among them,
// since tab groups (2026-09-04) section the strip by tag and a header's fold, chip, count and pip are paint
// too — and the one place that mutates the strip's DOM outside renderTabs, a tab drag's live reorder,
// resets it (a group drag moves no node: its drop is a views write the plan reads). The correctness of a
// signature skip rests on the input list being complete; this test is the list, so a new input the strip
// renders has to land here too. tab-strip-skip-exec.test.ts drives the same rule over a fake element tree.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const RENDER = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "render.ts"), "utf8");
const fn = RENDER.slice(RENDER.indexOf("function renderTabs() {"), RENDER.indexOf("function stripAftermath("));
const sig = fn.slice(fn.indexOf("const stripSig = JSON.stringify(["), fn.indexOf("const mslotEl = "));

test("the signature is computed before the wipe, and an equal one returns before any node is built", () => {
  assert.ok(fn.indexOf("const stripSig = JSON.stringify([") > 0, "renderTabs computes a signature");
  assert.ok(fn.indexOf("const stripSig = JSON.stringify([") < fn.indexOf("bar.replaceChildren();"), "signature before the wipe");
  assert.match(fn, /if \(stripSig === tabStripSig && !\(mslotEl && !mslotEl\.firstChild\)\) \{ stripAftermath\(visibleIds, ids\); return; \}\s*\n\s*tabStripSig = stripSig;/,
    "an equal signature keeps the DOM; the mobile slot's once-only mount still happens; the aftermath still reconciles");
  // the guards that already stood keep standing, ahead of the signature
  assert.ok(fn.indexOf("if (renameActive)") < fn.indexOf("const stripSig") && fn.indexOf("if (tabPointerHeld)") < fn.indexOf("const stripSig"));
  // the strip PLAN is computed ahead of the signature (it is an input), and the folded set it yields is
  // published before the skip: keyboard cycling (visibleOrder) reads it whether or not the strip rebuilt
  assert.ok(fn.indexOf("const plan = planStrip(") < fn.indexOf("const stripSig"), "the plan before the signature");
  assert.ok(fn.indexOf("collapsedTabIds = plan.folded;") < fn.indexOf("if (stripSig === tabStripSig"), "the folded set before the skip");
  // the focus capture + wipe keep their shape, now after the check: the header capture (tab-groups.test pins
  // its pair with the tab rule) then the tab rule, then the wipe
  assert.ok(fn.indexOf("const focusedGroup = ") > fn.indexOf("tabStripSig = stripSig;"), "the focus capture follows the skip");
  assert.match(fn, /const refocusTab = bar\.contains\(document\.activeElement\);\s*\n\s*bar\.replaceChildren\(\);/);
});

test("every input the strip renders is in the signature", () => {
  // the theme and colormap are inputs too: the context gauge's tone and fallback read the theme (pickTone,
  // ctxFallbackColor) and the compacting sweep's gradient the colormap, and a settings change repaints the
  // strip only through this signature. The plan's items carry each section's tag, color, members, fold
  // state, active mark and hidden members — what a group header paints (tab-groups.ts planStrip) — and
  // `unions` is the tag unions the filter chips render (the same viewTagUnion(effViews()) the plan read).
  for (const needle of [
    "activeId", "peekId", "phoneLayout()", "ids", "visibleIds", "tabInView(activeId)", "plan.items",
    "settings.tabCtx", "settings.stripGroupRows", "settings.theme", "settings.colormap", 'titleWithKey("Open a session", "session.new")',
    "settings.denseChrome",   // compact tabs: a body class re-heights every strip item with no width change, so only a rebuild lays the hairlines and keep breaks under the new rows (review round 2 of the keep-with-next change)
    'surfaceLens(effViews(), "chat")', "unions",
    "snapView",   // the section whose snapshot the pane shows: a header's snap-shown mark and its way-back act derive from it (makeGroupHead), and leaveSnapshot changes it with no fold change
    "m?.name", "m?.color?.bg", "m?.color?.fg", "m?.emoji",
    "s.name", "s.color?.bg", "s.color?.fg", "s.emoji ?? tabMeta.get(id)?.emoji", "st.state", "tabStateClass(st)", "!!st.faded",
    "st.ctx", "st.ctxColor", "st.ctxTone", "!!s.sub", "!!(s.userTodos && s.userTodos.length)", "hostIsDown(id)", "hostDownNote(id)",
    "ledgers.get(id)?.needsInput === true",   // the feed's needs-you verdict: a header's stand-in pip over its hidden members reads it (tab-snapshot.ts standInPip)
  ]) assert.ok(sig.includes(needle), "the signature reads " + needle);
  assert.match(fn, /const unions = viewTagUnion\(effViews\(\)\);\s*\n\s*const plan = planStrip\(visibleIds, unions, readTabGroups\(unions\), activeId, phoneLayout\(\),/,
    "the plan reads the unions the signature carries");
  assert.match(sig, /visibleIds\.map\(\(id\) => \{/, "per visible id: a placeholder's meta or the session's painted fields");
  // the state class the paint adds is the signature's own reading of the state: one rule for both — and for
  // the dot slot every tab carries (tabDotClass) and its hover title (tabDotTitle), which derive from st.state,
  // already in the signature (tab-state.ts, the shared module; the folded header's pip reads the same module)
  assert.match(fn, /const stateCls = tabStateClass\(s\.status\);\s*\n\s*if \(stateCls\) tab\.classList\.add\(stateCls\);/);
  const tabStateImport = RENDER.match(/^import \{([^}]*)\} from "\.\/tab-state";/m);
  assert.ok(tabStateImport, "render.ts imports from tab-state");
  for (const name of ["tabStateClass", "tabDotClass", "tabDotTitle"]) assert.ok(tabStateImport![1].split(",").map((s) => s.trim()).includes(name), "the tab-state import carries " + name);
});

test("a tab drag resets the signature (its live reorder changes the strip's DOM outside renderTabs), and the tooltip reads the session fresh", () => {
  // T264b (upstream) records the dragged node too (draggedEl); the signature reset follows it on the next line
  assert.match(fn, /tab\.addEventListener\("dragstart", \(e\) => \{\s*\n\s*draggedId = id; draggedEl = tab; tabDragCommitted = false;\s*\n\s*tabStripSig = "";/);
  assert.match(fn, /showTabTip\(tab, sessions\.get\(id\) \?\? s\)/, "a tab node now outlives a frame that replaced the session object");
  assert.match(RENDER, /^let tabStripSig = "";/m);
  // a GROUP drag needs no reset: its dragover only marks the drop target (no live reorder of headers — the
  // order is a kernel write) and its drop posts the tag order, which the plan reads on the next render
  const drag = RENDER.slice(RENDER.indexOf('tabs.addEventListener("dragover", (e) => {'), RENDER.indexOf('tabs.addEventListener("drop", (e) => {'));
  assert.match(drag, /if \(draggedGroup\) \{[^]*?No live reorder of headers[^]*?return;\s*\n\s*\}/);
});

test("what follows a render runs on both paths: the placeholder, the section snapshot's refresh and the all-hidden blank", () => {
  assert.match(RENDER, /function stripAftermath\(visibleIds: readonly string\[\], ids: readonly string\[\]\): void \{\s*\n\s*syncNoSessionsPlaceholder\(visibleIds\.length, ids\.length\);/);
  assert.equal((fn.match(/stripAftermath\(visibleIds, ids\)/g) || []).length, 2, "the skip path and the rebuild path");
  // the all-hidden blank reads the active view, which is built lazily and can appear between two equal
  // strips: it lives in the aftermath, not behind the skip (session-views pins the block's shape)
  const after = RENDER.slice(RENDER.indexOf("function stripAftermath("), RENDER.indexOf("// Right-click context menu on a tab."));
  assert.match(after, /const blank = !visibleIds\.length && ids\.length > 0 && !tabInView\(activeId\);/);
  assert.ok(!fn.includes("allHiddenBlanked"), "renderTabs itself does not blank or restore: only the aftermath, which both paths reach");
  // the snapshot's rows read a member's last event and working note, which the strip's signature does not carry:
  // a push that leaves the strip as it was still refreshes them (tab-snapshot-pane pins the block's shape)
  assert.match(after, /if \(snapView\) renderSnapshot\(\);/, "the snapshot refresh is in the aftermath, not behind the skip");
  assert.ok(!fn.includes("renderSnapshot("), "renderTabs itself does not call it: only the aftermath, which both paths reach");
  // …and the plan it reads is set before the skip returns
  assert.ok(fn.indexOf("lastStripItems = plan.items;") < fn.indexOf("const stripSig"), "lastStripItems is updated ahead of the skip");
});
