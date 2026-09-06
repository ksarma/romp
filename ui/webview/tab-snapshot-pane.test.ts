// THE SECTION SNAPSHOT, PANE SIDE (render.ts; the 2026-09-06 review of the tabsnapshot branch). The model
// and its words are tab-snapshot.ts (tab-snapshot.test.ts); this file pins how render.ts shows, leaves and
// protects the view: the section gone from the strip puts the transcript back; Escape and a second header
// click are the way back; a press on a row survives a rebuild; a remote row's host prefix is quiet metadata;
// a pick that lands on a still-loading tab hands the composer to the loading state; the client's Ledger type
// declares the field the now line reads. Source pins on render.ts (no jsdom here; the tab-groups.test.ts
// harness) plus executed checks on the pure modules. The notes-api demo world, synthetic ids, TESTHOST.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { viewTagUnion } from "./session-views";
import { parseTabGroups, planStrip, setSectionCollapsed, homeSectionOf } from "./tab-groups";
import { hostPrefix } from "./host-prefix";
import { noteLine } from "./tab-snapshot";

const ui = (...p: string[]) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", ...p), "utf8");
const RENDER = ui("webview", "render.ts");
const CSS = ui("webview", "styles.css");
const SNAP = RENDER.slice(RENDER.indexOf("let snapView: string | null = null;"), RENDER.indexOf("function showActive() {"));
const SHOW = RENDER.slice(RENDER.indexOf("function showActive() {"), RENDER.indexOf("function showActive() {") + 6500);
const TABS = RENDER.slice(RENDER.indexOf("function renderTabs() {"), RENDER.indexOf("function dismissTabMenu() {"));
const HEAD = RENDER.slice(RENDER.indexOf("function makeGroupHead("), RENDER.indexOf("function sectionHeadOf("));
const DELEGATE = RENDER.slice(RENDER.indexOf('"toggle-group": (el) => {'), RENDER.indexOf('"toggle-group": (el) => {') + 1400);

const V = {
  active: "all",
  tags: [
    { id: "g1", name: "qa", color: "#DD42FF", members: ["tests", "api"] },
    { id: "g2", name: "infra", color: "#4EC9B0", members: ["web", "api"] },
  ],
};

test("the section gone from the strip while its snapshot shows puts the transcript back (HIGH, review finding 5)", () => {
  // renderTabs dropped renderSnapshot's answer: the shown section leaving the plan (its tag deleted or renamed,
  // its last member hidden or moved out, sectioning turned off) cleared snapView and hid the host, and nothing
  // showed the transcript again: every view display:none, the composer disabled under the snapshot's
  // placeholder, until the user happened to click a tab. The absence from the plan is the event; the same
  // renderTabs answers it with showActive, which re-enables the composer.
  assert.match(TABS, /collapsedTabIds = plan\.folded;\s*\n\s*lastStripItems = plan\.items;/, "the plan renderSnapshot reads is the one just rendered");
  assert.match(TABS, /const shown = snapView;\s*\n\s*if \(snapView\) renderSnapshot\(\);\s*\n\s*if \(shown && !snapView\) showActive\(\);/,
    "renderSnapshot clears snapView when the section is not in the plan; the transcript comes back in the same render");
  assert.match(SNAP, /if \(!head\) \{ snapView = null; hideSnapshot\(\); return false; \}/, "the section's absence is the event");
  assert.match(SHOW, /hideSnapshot\(\);\s*\n\s*const s = activeId \? sessions\.get\(activeId\) : null;/, "showActive's transcript path hides the host…");
  assert.match(SHOW, /composer\.disabled = closed;\s*\n\s*composer\.placeholder = closed \? "Session closed — read-only" : composerRestingPlaceholder\(\);/, "…and re-enables the composer for a live session");
  // executed: the event on the real planner. The shown section's last visible member gone → no header of that name
  const unions = viewTagUnion(V);
  const st = parseTabGroups(null);
  const heads = (visible: string[], groups = st) => planStrip(visible, unions, groups, "web", false).items.filter((i) => "head" in i).map((i) => ("head" in i ? i.head.name : ""));
  assert.deepEqual(heads(["web", "api", "tests"]), ["qa", "infra"]);
  assert.deepEqual(heads(["api", "tests"]), ["qa"], "infra's last visible member hidden: no infra header, so renderSnapshot finds none and clears the view");
  assert.deepEqual(heads(["web", "api", "tests"], { ...st, on: false }), [], "sectioning off: the flat strip, no headers at all");
  assert.equal(homeSectionOf(planStrip(["api", "tests"], unions, st, "web", false).items, "web"), null, "the active id has no home on that strip either");
});

test("the way back (review findings 6 and 12): Escape leaves the snapshot when no layer owns it; the open, shown header of the section holding the active tab offers the transcript on its second click", () => {
  // every header click set snapView and only a session pick cleared it: a mis-click on a header cost the
  // transcript and two more gestures. The click-to-snapshot is the user's ask and stays; these are the exits.
  assert.match(SNAP, /function leaveSnapshot\(\): void \{\s*\n\s*if \(!snapView\) return;\s*\n\s*snapView = null;\s*\n\s*renderTabs\(\);\s*\n\s*showActive\(\);\s*\n\}/,
    "one exit: snapView cleared, the header's mark dropped by the strip render, the transcript and the live composer back through showActive");
  // Escape: two phases on the window (tab-snapshot-view.ts installSnapshotEscape, executed in its own test): armed at
  // capture, so this page's layers that own their own Escape are still on the page to be seen and yielded to;
  // decided at bubble, after the shell's Escape chain (document capture in this frame, kernel.py _LANDING_ESC_JS)
  // has closed and stopped an Escape aimed at one of its panels (the log, usage and network panels live in the
  // shell document, out of this page's sight; round 2: the one-phase handler swapped the pane on those too)
  const esc = SNAP.slice(SNAP.indexOf("// ESCAPE LEAVES THE SNAPSHOT"), SNAP.indexOf("/** Paint (or refresh) the snapshot"));
  assert.match(esc, /installSnapshotEscape\(window, \{\s*\n\s*showing: \(\) => !!snapView,\s*\n\s*typing: isTypingTarget,/, "only while the snapshot shows; a field keeps its Escape");
  assert.match(esc, /layerOpen: \(\) => !!\(ctxMenuEl \|\| metaMenuEl \|\| citePreviewEl \|\| openCommentKey \|\| document\.querySelector\("\.picker-overlay"\)\)/, "menus, a preview, a comment thread, the picker and confirm overlays own theirs");
  assert.match(esc, /\|\| !!document\.querySelector\("#rsettings:not\(\[hidden\]\), #ra-back:not\(\[hidden\]\)"\)/, "the pane's own panels");
  assert.doesNotMatch(esc, /rkeys-back/, "the shortcuts dialog is the shell document's: that selector never matched here (dead), and its Escape never reaches this frame");
  assert.match(esc, /romp-fileview[\s\S]*romp-filebrowse[\s\S]*romp-lightbox/, "the full-pane surfaces");
  assert.match(esc, /leave: leaveSnapshot,\s*\n\}\);/, "one exit");
  assert.doesNotMatch(esc, /window\.addEventListener/, "no listener of its own: the module owns the two phases");
  // the tab menu's closer runs before it (registered earlier, capture too) and now marks the Escape it consumed
  assert.match(RENDER, /window\.addEventListener\("keydown", \(e\) => \{ if \(e\.key === "Escape" && ctxMenuEl\) \{ dismissTabMenu\(\); e\.preventDefault\(\); \} \}, true\);/,
    "an Escape that closed the tab menu says so, and the snapshot's handler yields to it");
  // the header: the act derived from the rendered state (open + shown + holds the active tab), like the fold's data-folded
  assert.match(HEAD, /head\.dataset\.act = "toggle-group";\s*\n\s*head\.dataset\.folded = collapsed \? "1" : "0";\s*\n\s*if \(snapView === name\) head\.classList\.add\("snap-shown"\);/, "every header folds and shows the section…");
  assert.match(HEAD, /const back = snapView === name && !collapsed && holdsActive;\s*\n\s*if \(back\) head\.dataset\.act = "show-transcript";/, "…except the one whose click is being undone");
  assert.match(HEAD, /const words = headWords\(name, total, hidden\.length, collapsed, holdsActive, back\);/, "the title and the spoken label say which click this is (tab-groups.test.ts executes the words)");
  // to assistive tech the way-back header is a plain button, not a disclosure (round 2): it announced "expanded"
  // and pressing it folded nothing, so aria-expanded is left off in that state; the label (headWords) names the action
  assert.match(HEAD, /if \(!back\) head\.setAttribute\("aria-expanded", collapsed \? "false" : "true"\);/, "no aria-expanded on the header whose press puts the transcript back");
  assert.equal(HEAD.split('"aria-expanded"').length - 1, 1, "and nowhere else is it set on a header");
  assert.match(DELEGATE, /"show-transcript": \(\) => leaveSnapshot\(\),/, "the delegate's handler, on the stable #tabs root like toggle-group");
  assert.match(DELEGATE, /"toggle-group": \(el\) => \{\s*\n\s*const name = el\.dataset\.group;\s*\n\s*if \(!name\) return;\s*\n\s*snapView = name;/, "toggle-group itself is unchanged: a header click shows the section (the user's ask)");
  // a folded header holding the active tab is never `back`: the fold is the rendered state the click acts on
  const unions = viewTagUnion(V);
  const folded = setSectionCollapsed(parseTabGroups(null), "infra", true);
  const inf = planStrip(["web", "api", "tests"], unions, folded, "web", false).items.find((i) => "head" in i && i.head.name === "infra") as { folded: boolean; active: boolean };
  assert.deepEqual([inf.folded, inf.active], [true, true], "folded + active: the click opens (toggle-group); the header re-renders open + shown + active, and THAT click is the way back");
});

test("snapshot rows are click-safe (review finding 7): a press latches the strip's hold, so no rebuild lands between mousedown and mouseup", () => {
  // the delegate on the stable host was half of the rule; the strip needed the other half too (tabPointerHeld):
  // a replaceChildren mid-press leaves the click with no [data-act] node under it: the "had to click it
  // several times" bug ui/CLAUDE.md names. One latch for the two surfaces, one release path.
  assert.match(SNAP, /host\.addEventListener\("pointerdown", \(\) => \{ tabPointerHeld = true; \}\);\s*\n\s*return host;/, "installed once, with the host (snapshotHost makes it once)");
  assert.equal(SNAP.split("delegate(host").length - 1, 1, "still one delegate, never in the render");
  assert.match(SNAP, /if \(tabPointerHeld && host\.childElementCount\) \{ renderPendingWhilePressed = true; return true; \}\s*\n\s*snapModel = next;/,
    "renderSnapshot's own rebuild (showActive can reach it mid-press) waits for the release; the times still ticked in place above");
  assert.match(RENDER, /function renderTabs\(\) \{[\s\S]{0,600}?if \(tabPointerHeld\) \{ renderPendingWhilePressed = true; return; \}/, "renderTabs, the row rebuild's usual caller, already waits");
  assert.match(RENDER, /function releaseTabStrip\(\): void \{\s*\n\s*if \(!tabPointerHeld\) return;\s*\n\s*tabPointerHeld = false;\s*\n\s*if \(renderPendingWhilePressed\) \{ renderPendingWhilePressed = false; setTimeout\(\(\) => renderTabs\(\), 0\); \}/,
    "the release flushes renderTabs, which renders the snapshot (the follow above)");
  for (const ev of ["pointerup", "pointercancel", "blur"]) assert.match(RENDER, new RegExp(`window\\.addEventListener\\("${ev}", releaseTabStrip\\)`), "released on " + ev);
});

test("a row whose session left the strip mid-press opens nothing (round 2): the delegate checks the row's session is still on the strip before setActive", () => {
  // the rule executes in tab-snapshot-view.test.ts (rowStillOpen); this pins that the one delegate applies it, with
  // the row's own loading flag (a placeholder's row is allowed its meta alone), the maps, and the close suppression
  const open = SNAP.slice(SNAP.indexOf("delegate(host, {"), SNAP.indexOf("host.addEventListener(\"pointerdown\""));
  assert.match(open, /const id = node\.dataset\.id;\s*\n\s*if \(!id\) return;/, "the id off the row");
  assert.match(open, /if \(!rowStillOpen\(snapModel\?\.rows\.find\(\(r\) => r\.id === id\), sessions\.has\(id\), tabMeta\.has\(id\), closingTabs\.has\(id\)\)\) return;\s*\n\s*setActive\(id\); focusActiveTab\(\);/,
    "the row's session must still be on the strip; otherwise nothing moves (the release's flush repaints without the row)");
  assert.equal(SNAP.split("delegate(host").length - 1, 1, "still one delegate, on the stable host");
});

test("a remote row's host prefix is quiet metadata, not part of the bold name (review finding 2)", () => {
  assert.match(SNAP, /const name = el\("span", "snap-sess"\); name\.replaceChildren\(\.\.\.hostNameNodes\(r\.name, r\.id\)\);/, "the tab's helper (host-prefix.ts), one class for every surface");
  assert.doesNotMatch(SNAP, /name\.textContent = r\.name;/, "the raw frame name is not written as one text node");
  assert.match(SNAP, /if \(r\.color\) name\.style\.color = r\.color\.bg;/, "the identity color stays on the name; .host-prefix sets its own dim color and weight");
  // executed: the split the row will render, on a TESTHOST-prefixed synthetic id
  assert.deepEqual(hostPrefix("TESTHOST:web", "TESTHOST:11111111-2222-3333-4444-555555555555"), { host: "TESTHOST:", rest: "web" });
  assert.equal(hostPrefix("web", "11111111-2222-3333-4444-555555555555"), null, "a local row: the plain name");
  assert.equal(hostPrefix("web", "TESTHOST:11111111-2222-3333-4444-555555555555"), null, "a remote id whose name federation did not prefix: the plain name too");
});

test("a pick that lands on a still-loading tab hands the composer to the loading state (review finding 12, second half)", () => {
  // showActive's loading branch never touched the composer, so a snapshot row's "opening…" session kept the
  // snapshot's disabled box and its "pick a session" placeholder, after the user had just picked one
  const loading = SHOW.slice(SHOW.indexOf("if (activeId && tabMeta.has(activeId)) {"), SHOW.indexOf("} else if (!empty) {"));
  assert.match(loading, /content\.appendChild\(wait\);\s*\n\s*if \(empty\) empty\.style\.display = "none";/, "the loader in the transcript's place, as before");
  assert.match(loading, /const ta = document\.getElementById\("composer-input"\) as HTMLTextAreaElement \| null;\s*\n\s*if \(ta\) \{ ta\.disabled = false; ta\.placeholder = composerRestingPlaceholder\(\); \}\s*\n\s*const sendBtn = document\.getElementById\("composer-send"\) as HTMLButtonElement \| null;\s*\n\s*if \(sendBtn\) sendBtn\.disabled = false;/,
    "the box takes input for the picked session; the first frame's showActive sets its closed/live state");
  assert.match(SHOW, /if \(ta\) \{ ta\.disabled = true; ta\.placeholder = "Pick a session above to write to it"; \}/, "the snapshot's own disable stands while the snapshot shows");
});

test("the client's Ledger type declares the two fields the snapshot reads off the ledger: workingNote (the note line) and needsInput (the feed's needs-you word) (review finding 15; round 2)", () => {
  // round 1 added workingNote and its comment said the note fed the now line; the note is the row's second
  // line now, and needsInput (the kernel's build_session puts the feed's verdict on the ledger) had no
  // declared source on the client, so a read of ledgers.get(id)!.needsInput failed typecheck for a field
  // every ledger carries. Both optional: a remote host's older kernel sends neither.
  assert.match(RENDER, /^interface Ledger \{ summary: string; tree\?: LedgerTreeNode\[\]; current\?: \{ t\?: number \} \| null; recent\?: LedgerRecent\[\]; workingNote\?: string; needsInput\?: boolean \| null; \}/m,
    "optional on the wire: a remote host's older kernel sends none");
  const line = RENDER.split("\n").find((l) => l.startsWith("interface Ledger {")) || "";
  assert.match(line, /workingNote: the session's postal working note[^\n]*the snapshot row's second line/, "the comment says where the note goes now (the row's second line, not the now line)");
  assert.match(line, /needsInput: the feed's needs-you verdict/, "…and names the second field's source");
  assert.doesNotMatch(line, /now line/, "the stale 'now line' claim is gone");
  assert.match(RENDER, /snapshotModel\(head\.head, \(id\) => sessions\.get\(id\) \?\? null, \(id\) => ledgers\.get\(id\) \?\? null, snapModel\)/, "the ledger the model reads is the client's Ledger");
});

test("the row's second line: the session's own working note, quieter, under the now line (tab-snapshot.ts SnapRow.note, the model's request of the renderer)", () => {
  // the model moved the postal working note out of the now line (it is the session's claim to a branch and
  // files, written for peers) and onto the row as its own field; the renderer and the sheet paint it
  assert.match(SNAP, /if \(r\.note\) \{\s*\n(?:\s*\/\/[^\n]*\n)*\s*const note = el\("span", "snap-note"\); note\.textContent = r\.note; note\.setAttribute\("aria-hidden", "true"\);\s*\n\s*btn\.appendChild\(note\);\s*\n\s*\}\s*\n\}/,
    "appended last (fillSnapshotRow's last part), so the wrapping row puts it under the first line's parts; spoken by the label (rowWords), like the flag");
  const block = CSS.slice(CSS.indexOf("#tab-snapshot {"), CSS.indexOf(".snap-when {") + 400);
  assert.match(block, /\.snap-row \{ display: flex; flex-wrap: wrap; align-items: center; gap: 2px 8px;/, "the row wraps: the note takes the second line, a hair below");
  assert.match(block, /\.snap-note \{ flex: 1 0 100%; min-width: 0; padding-left: 15px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 0.82em; color: var\(--dim\); opacity: 0\.7; \}/,
    "the header's 0.82em (the sheet's one sub-line size), the dim token a step quieter, one line, indented past the pip (7px) and its gap (8px)");
  assert.equal(noteLine({ summary: "", workingNote: "  own branch web; editing the list page  " }), "own branch web; editing the list page", "the model's line is the text painted");
  assert.equal(noteLine({ summary: "Building the notes-api web pages" }), "", "no note: no second line (the `if (r.note)`)");
});

test("snapshot rows update in place, keyed by session id, so the row a keyboard user is on and a hover's title survive the push that changes a row (round 2)", () => {
  // every model change repainted the rows with host.replaceChildren; sameRow folds lastT and lastMsg, so the rows
  // rebuilt on nearly every push while a member worked, and the button the user had Tabbed onto was destroyed under
  // them within seconds (focus to body; Enter did nothing, the composer being disabled under the snapshot). The
  // strip keeps focus across its rebuild by re-focusing the active tab (renderTabs); the rows keep it by keeping
  // their NODES: tab-snapshot-view.ts reconcileRows (executed in tab-snapshot-view.test.ts) patches the standing
  // row nodes, makes and removes only the rows that came and went, and moves only a reordered one. The event is
  // the push that changed the model; the same-object path above it still moves nothing but the ago texts.
  const paint = SNAP.slice(SNAP.indexOf("function renderSnapshot(): boolean {"), SNAP.indexOf("function snapshotRowNode("));
  assert.match(paint, /if \(next === snapModel && host\.childElementCount\) \{/, "the same-object gate stands");
  assert.equal(paint.split("host.replaceChildren(").length - 1, 1, "the host's children are replaced once: the first paint");
  assert.match(paint, /let list = host\.querySelector<HTMLElement>\("\.snap-list"\);\s*\n\s*if \(!list\) \{[\s\S]*?host\.replaceChildren\(h, list\);\s*\n\s*\}/, "the heading and the list are made once, with the host's first paint");
  assert.match(paint, /part\("snap-name"\)\.textContent = next\.name;\s*\n\s*part\("snap-count"\)\.textContent = words\.count;/, "the heading's parts are patched, not remade");
  assert.match(paint, /reconcileRows<SnapRow, Element>\(list, next\.rows, \(n\) => n\.getAttribute\("data-id"\), \(r\) => snapshotRowNode\(r, now\), \(n, r\) => fillSnapshotRow\(n\.firstElementChild as HTMLElement, r, now\)\);/,
    "keyed by the row's session id: a new row's node from snapshotRowNode, a standing row's parts from fillSnapshotRow");
  assert.doesNotMatch(paint, /for \(const r of next\.rows\) list\.appendChild/, "no wholesale row build");
  // a MOVED row: insertBefore detaches and re-attaches its node, which blurs it (the browser's focus fixup); the same
  // event puts focus back on it (the strip's refocus rule, by node instead of by id). A row GONE from under focus
  // (its session left the section): the row now in its place takes it, the last when it was last, so the keyboard
  // user is not dropped to body by a removal either
  assert.match(paint, /const focused = document\.activeElement as HTMLElement \| null;\s*\n\s*const focusedAt = focused && list\.contains\(focused\) \? Array\.from\(list\.children\)\.indexOf\(focused\.closest\("\.snap-item"\)!\) : -1;\s*\n\s*reconcileRows<SnapRow, Element>\(/,
    "the focused node and its place, read before the update");
  assert.match(paint, /if \(focused && list\.contains\(focused\)\) \{ if \(document\.activeElement !== focused\) focused\.focus\(\); \}/, "moved: put back");
  assert.match(paint, /else if \(focusedAt >= 0 && list\.children\.length\) list\.children\[Math\.min\(focusedAt, list\.children\.length - 1\)\]\.querySelector<HTMLElement>\("\.snap-row"\)\?\.focus\(\);/, "gone: the row in its place");
  // the row node: the item carries the key; the button (Tab's target, the title's owner) is filled by the same function a
  // patch calls, so a made row and a patched row have one shape
  const node = SNAP.slice(SNAP.indexOf("function snapshotRowNode("), SNAP.indexOf("function fillSnapshotRow("));
  assert.match(node, /item\.dataset\.id = r\.id;/, "the key, on the item the list holds");
  assert.match(node, /fillSnapshotRow\(btn, r, now\);\s*\n\s*item\.appendChild\(btn\);\s*\n\s*return item;/, "one fill for both paths");
  const fill = SNAP.slice(SNAP.indexOf("function fillSnapshotRow("), SNAP.indexOf("function showActive() {"));
  assert.match(fill, /btn\.className = "snap-row" \+ \(r\.closed \? " closed" : ""\) \+ \(r\.loading \? " loading" : ""\);/, "the classes rewritten, not toggled one by one");
  assert.match(fill, /btn\.replaceChildren\(\);/, "the parts emptied, then appended in order: the button stands");
  assert.match(fill, /const nowEl = el\("span", "snap-now"\); nowEl\.textContent = r\.loading \? "opening…" : r\.now; btn\.appendChild\(nowEl\);/, "the parts as before");
  // the sheet: the focus ring is on the button, the node that stands
  assert.match(CSS, /\.snap-row:focus-visible \{ outline: 1px solid var\(--accent\); outline-offset: -1px; \}/);
});
