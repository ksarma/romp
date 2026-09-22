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
    "snapView",   // the section the pane shows at a glance: a header's mark, its way-back act and its words derive from it
    "m?.name", "m?.color?.bg", "m?.color?.fg", "m?.emoji",
    "s.name", "s.color?.bg", "s.color?.fg", "s.emoji ?? tabMeta.get(id)?.emoji", "st.state", "tabStateClass(st)", "!!st.faded",
    "st.ctx", "st.ctxColor", "st.ctxTone", "!!s.sub", "!!(s.userTodos && s.userTodos.length)", "hostIsDown(id)", "hostDownNote(id)",
    "ledgers.get(id)?.needsInput === true",   // the feed's needs-you verdict: a header's stand-in pip over its hidden members reads it (tab-snapshot.ts standInPip)
    "settings.tabWidgets", "tabHotkey(id)",   // T379: which widgets a tab carries (and their options), and the hot-key keycap's chord
    "st.needsYou === true", "kst?.needsYou === true",   // the yellow ring's input (the ask ring, 2026-09-13; a widget since 2026-09-14): a card of the session's entering or leaving the feed's needs-you column repaints, on a loaded tab and a skeleton alike; the switches ride settings.tabWidgets above
  ]) assert.ok(sig.includes(needle), "the signature reads " + needle);
  assert.match(fn, /const unions = viewTagUnion\(effViews\(\)\);\s*\n\s*const plan = planStrip\(visibleIds, unions, readTabGroups\(unions\), activeId, phoneLayout\(\),/,
    "the plan reads the unions the signature carries");
  assert.match(sig, /visibleIds\.map\(\(id\) => \{/, "per visible id: a placeholder's meta or the session's painted fields");
  // the state class the paint adds is the signature's own reading of the state: one rule for both — and for
  // the dot slot every tab carries (tabDotClass) and its hover title (tabDotTitle), which derive from st.state,
  // already in the signature (tab-state.ts, the shared module; the folded header's pip reads the same module)
  // …applied in applyTabStatus, the chip helper renderTabs shares with the skeleton tab (2026-09-07)
  const chip = RENDER.slice(RENDER.indexOf("function applyTabStatus("), RENDER.indexOf("function wireTabDrag("));
  assert.match(fn, /const st = applyTabStatus\(tab, s\);/);
  assert.match(chip, /const stateCls = tabStateClass\(s\.status\);\s*\n\s*if \(stateCls\) tab\.classList\.add\(stateCls\);/);
  // the dot is a WIDGET since T379 (tab-widgets.ts): its render is the one rule's site, and the fork's hover title rides it
  // there (tabDotTitle right after tabDotClass, the 2026-09-10 fold's twin), so a skeleton tab's pip explains itself too
  const TW = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "tab-widgets.ts"), "utf8");
  assert.match(TW, /const cls = tabDotClass\(status\.state\);[^]*?const tip = tabDotTitle\(status\.state\);\s*\n\s*if \(tip\) d\.title = tip;/,
    "tabDotTitle is applied inside the dot widget's render, on the dot the one rule classed");
  // render.ts imports the state rule and the section pip's title from tab-state (this fork adds its tabhide names to the same
  // line, so the pin reads the names, not one exact line), and neither dot name any more: the widget imports both itself
  const tabStateImport = RENDER.match(/^import \{([^}]*)\} from "\.\/tab-state";/m);
  assert.ok(tabStateImport, "render.ts imports from tab-state");
  const tabStateNames = tabStateImport![1].split(",").map((s) => s.trim());
  for (const name of ["tabStateClass", "sectionPipTitle"]) assert.ok(tabStateNames.includes(name), "the tab-state import carries " + name);
  for (const name of ["tabDotClass", "tabDotTitle"]) assert.ok(!tabStateNames.includes(name), "the dot rule moved into the dot widget (T379): render.ts no longer imports " + name);
  assert.match(RENDER, /^import \{ composeTabWidgets, composeTabRing, ringSwitch, tabHotkey, miniChord \} from "\.\/tab-widgets";/m, "the widgets the strip composes (the rings too, one class at a time), the ring switches the folded pip reads, and the hot-key chord the signature reads");
});

test("a tab drag resets the signature (its live reorder changes the strip's DOM outside renderTabs), and the tooltip reads the session fresh", () => {
  // the listeners live in wireTabDrag, shared with the skeleton tab (2026-09-07); renderTabs wires every loaded tab through it.
  // T264b (upstream) records the dragged node too (draggedEl); the signature reset follows it on the next line
  assert.match(fn, /wireTabDrag\(tab, id\);/);
  const wire = RENDER.slice(RENDER.indexOf("function wireTabDrag("), RENDER.indexOf("function makeSkeletonTab("));
  assert.match(wire, /tab\.addEventListener\("dragstart", \(e\) => \{\s*\n(?:\s*if \(fedMissing \|\| settings\.tabsLocked\) \{ e\.preventDefault\(\); return; \}[^\n]*\n)?\s*draggedId = id; draggedEl = tab; tabDragCommitted = false;\s*\n\s*tabStripSig = "";/);   // the manager-missing refusal may lead (2026-09-10)
  assert.match(fn, /showTabTip\(tab, sessions\.get\(id\) \?\? s\)/, "a tab node now outlives a frame that replaced the session object");
  assert.match(RENDER, /^let tabStripSig = "";/m);
  // a GROUP drag needs no reset: its dragover only marks the drop target (no live reorder of headers — the
  // order is a kernel write) and its drop posts the tag order, which the plan reads on the next render
  const drag = RENDER.slice(RENDER.indexOf('tabs.addEventListener("dragover", (e) => {'), RENDER.indexOf('tabs.addEventListener("drop", (e) => {'));
  assert.match(drag, /if \(draggedGroup\) \{[^]*?No live reorder of headers[^]*?return;\s*\n\s*\}/);
});

test("the column partition (the chat split, 2026-09-11): the sets are read once at the top, ahead of the filter and the plan, and tabInView reads columnHolds", () => {
  const read = fn.indexOf("colSets = readColSets();");
  assert.ok(read > 0 && read < fn.indexOf("const visibleIds = ids.filter((id) => stripShows(id, only));"), "one cross-window read per render, before the filter (stripShows reads tabInView, which reads the sets)");
  assert.equal((fn.match(/readColSets\(\)/g) || []).length, 1, "read once");
  assert.ok(read < fn.indexOf("const plan = planStrip("), "before the plan, which reads visibleIds");
  assert.match(RENDER, /function heldHere\(id: string\): boolean \{ return isSubId\(id\) \|\| isProvisionalId\(id\) \|\| columnHolds\(colSets, COL, id\); \}/,
    "a sub-agent viewer and a provisional tab are the page's own; every other id is the shell's sets' to place");
  assert.match(RENDER, /function tabInView\(id: string\): boolean \{ return \(id === peekId \|\| chatVisible\(id\)\) && heldHere\(id\); \}/);
  assert.match(RENDER, /^import \{ colFromSearch, columnHolds, columnEmptiness, type ColSets \} from "\.\/chat-columns";/m);   // …and the emptiness verdict (the host rule, 2026-09-14)
  assert.match(RENDER, /^const COL = colFromSearch\(location\.search\);/m);
  // the skip line and the signature list are unchanged: the partition reaches the signature through ids and visibleIds
  assert.match(fn, /if \(stripSig === tabStripSig && !\(mslotEl && !mslotEl\.firstChild\)\) \{ stripAftermath\(visibleIds, ids\); return; \}/);
  assert.ok(!sig.includes("colSets"), "the sets are not a signature input of their own: visibleIds already carries the filter");
  // …and the shell's write of the sets re-renders through the storage event (the tab-groups idiom)
  assert.match(RENDER, /window\.addEventListener\("storage", \(e\) => \{ if \(e\.key === "romp-chat-cols"\) renderTabs\(\); \}\);/);
});

test("what follows a render runs on both paths: the placeholder, the section snapshot's refresh and the all-hidden blank", () => {
  assert.match(RENDER, /function stripAftermath\(visibleIds: readonly string\[\], ids: readonly string\[\]\): void \{\s*\n\s*syncNoSessionsPlaceholder\(visibleIds\.length, ids\.length, ids\.filter\(heldHere\)\.length\);/);   // + how many this column holds (the chat split's copy, 2026-09-11)
  assert.match(RENDER, /const shown = snapView;\s*\n\s*const held = shown \? snapshotHoldsFocus\(\) : false;\s*\n\s*if \(snapView\) renderSnapshot\(\);/, "the section snapshot's refresh follows the placeholder (this fork's section at a glance)");
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

test("a skeleton tab is an input of its own: the kind, the strip meta and the stored status frame, never the stale session's status", () => {
  // the reconnect regime (2026-09-09): a skeleton id may still hold its pre-outage session in memory, so a
  // signature that read only `sessions` was equal before and after the kernel's skeleton list landed — and the
  // strip never repainted into skeletons. The skeleton's own reads join the list ahead of the session's.
  assert.match(sig, /if \(renderKind\(skeletonTabs, id, !!s\) === "skeleton"\) \{/, "the kind is decided inside the signature");
  assert.match(sig, /skeletonTabs\.status\.get\(id\)/, "the stored status frame is an input");
  assert.match(sig, /return \["k", m\?\.name \|\| s\?\.name,/, "a skeleton row is keyed apart from a placeholder's and a session's");
  assert.ok(sig.indexOf('=== "skeleton"') < sig.indexOf('return ["p", m?.name'), "the skeleton branch precedes the placeholder branch, as in the render loop");
});


test("census: every s.-sourced glyph input of the loaded row has an m?. or kst?. counterpart in the skeleton AND placeholder rows, or an exemption named here and checked against the builder", () => {
  // THE RULE (the user 2026-09-22, whose flagged sessions wore no flag until their tab was clicked): a glyph the strip
  // paints for a LISTED tab rides a frame every chat client receives for every listed tab, whatever kind the tab is drawn
  // as. The loaded row reads the session payload (s., st.); the skeleton diet and the cold-tab gate withhold that payload
  // for a tab nobody has opened, so the skeleton and placeholder rows read the strip meta (m?., the tabOrder row) and the
  // kernel's status frames (kst?.). An input the loaded row reads with NO counterpart in those rows is a glyph that never
  // draws before a click: the user-todo flag was one, folded in after the two rows were written, and this census at that
  // head listed it as missing from both rows. Rather than pin the one input, the census derives the loaded row's s.- and st.-sourced inputs
  // and demands each one's counterpart, or an exemption NAMED below and checked against the builder's source, so a
  // builder that starts painting an exempt input turns its exemption stale and the census demands the term.
  // the rows' comments, block and trailing, name other rows' reads: read the code alone (a term spelled only in a comment is
  // not a read, and the census must miss it; the block form is stripped first, so a `//` inside one cannot eat a line of code)
  const comments = (t: string) => t.replace(/\/\*[\s\S]*?\*\//g, "").replace(/\/\/[^\n]*/g, "");
  const rowAt = (start: number, label: string): string => {
    assert.ok(start >= 0, `the ${label} row is in the signature`);
    const a = sig.indexOf("return [", start), b = sig.indexOf("];", start);
    assert.ok(a >= start && b > a, `the ${label} row opens and closes`);
    return comments(sig.slice(a, b));
  };
  const skeleton = rowAt(sig.indexOf('return ["k",'), "skeleton"), placeholder = rowAt(sig.indexOf('return ["p",'), "placeholder");
  const loadedAt = sig.indexOf("const st = s.status;");
  assert.ok(loadedAt > sig.indexOf('return ["p",'), "the loaded row follows the placeholder branch, as in the render loop");
  const loaded = rowAt(loadedAt, "loaded");
  const fields = (row: string, re: RegExp): string[] => [...new Set([...row.matchAll(re)].map((m) => m[1]))];
  const sFields = fields(loaded, /\bs\.(\w+)/g);     // the session payload's own fields the loaded row paints from
  const stFields = fields(loaded, /\bst\.(\w+)/g);   // its status's fields (st = s.status)
  assert.ok(sFields.length >= 3 && stFields.length >= 3, `the derivation read the loaded row (an empty set would pass every check): s.${sFields.join(", s.")}; st.${stFields.join(", st.")}`);
  assert.ok(sFields.includes("userTodos"), "the loaded row paints the user-todo flag from s.userTodos (tab-usertodo.test.ts): the input this census was written for");
  assert.ok(loaded.includes("tabStateClass(st)"), "the loaded row's state class derives from st too");
  // the builders, for the exemption checks (each slice ends at its function's own close)
  const builder = (name: string): string => { const i = RENDER.indexOf(`function ${name}(`); assert.ok(i >= 0, name + " is in render.ts"); return RENDER.slice(i, RENDER.indexOf("\n}\n", i) + 3); };
  const skBuilder = builder("makeSkeletonTab"), phBuilder = builder("makePlaceholderTab");
  // EXEMPTIONS: an input a builder does not paint has no counterpart to demand. Each names the row and the field and
  // states what the builder's source must show for it to hold.
  const exempt: Array<[row: "skeleton" | "placeholder", field: string, holds: () => void]> = [
    ["skeleton", "emoji", () => assert.doesNotMatch(skBuilder, /tabEmojiNode\(/,
      "makeSkeletonTab paints no emoji today (the loaded and placeholder tabs do); once it does, the skeleton row owes m?.emoji")],
    ["skeleton", "sub", () => assert.doesNotMatch(skBuilder, /\bsub\b/,
      "a sub-agent viewer is client-only (the kernel never lists it on the roster), so it is never drawn as a skeleton; the builder reads no sub flag")],
    ["placeholder", "sub", () => assert.doesNotMatch(phBuilder, /\bsub\b/,
      "a sub-agent viewer is client-only, so it is never drawn as a placeholder; the builder reads no sub flag")],
  ];
  const placeholderReadsNoStatus = () => assert.doesNotMatch(phBuilder, /skeletonTabs\.status|applyTabStatus\(|appendTabAfterWidgets\(|\.status\b/,
    "makePlaceholderTab reads no status frame (a placeholder's session is still being built; a held status is a skeleton's), so every st. input is exempt for its row while that holds");
  const misses: string[] = [];
  for (const f of sFields) {
    for (const [row, text] of [["skeleton", skeleton], ["placeholder", placeholder]] as const) {
      const ex = exempt.find((e) => e[0] === row && e[1] === f);
      if (ex) { ex[2](); continue; }
      if (!text.includes(`m?.${f}`)) misses.push(`${row} row: no m?.${f} for the loaded row's s.${f}`);
    }
  }
  for (const f of stFields) {
    if (!skeleton.includes(`kst?.${f}`)) misses.push(`skeleton row: no kst?.${f} for the loaded row's st.${f}`);
    placeholderReadsNoStatus();
  }
  if (!skeleton.includes("tabStateClass(kst)")) misses.push("skeleton row: no tabStateClass(kst) for the loaded row's tabStateClass(st)");
  assert.deepEqual(misses, [],
    "a glyph input the loaded row paints and a skeleton or placeholder row does not carry never repaints for a listed tab whose payload this page has not been served: add the meta term to that row (and the glyph to its builder), or an exemption above that names why the builder cannot paint it");
});
